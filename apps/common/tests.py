import io
from PIL import Image
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from apps.admin_dashboard.models import AdminProfile
from apps.posts.models import Post
from apps.portfolio.models import Project
from apps.marketplace.models import Collaboration
from apps.chat.models import Conversation, Message
from apps.common.file_validation import validate_uploaded_image

User = get_user_model()


class HiveSecurityAuditTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Superadmin user
        self.super_admin = User.objects.create_superuser(
            email='superadmin@hive.com',
            password='SuperPassword123!',
            first_name='Super',
            last_name='Admin'
        )
        AdminProfile.objects.get_or_create(
            user=self.super_admin,
            defaults={'role': AdminProfile.Role.SUPER_ADMIN, 'is_active': True}
        )

        # Admin user (not superadmin)
        self.admin = User.objects.create_user(
            email='adminstaff@hive.com',
            password='StaffPassword123!',
            first_name='Staff',
            last_name='Admin',
            is_staff=True
        )
        AdminProfile.objects.get_or_create(
            user=self.admin,
            defaults={'role': AdminProfile.Role.CONTENT_MODERATOR, 'is_active': True}
        )

        # Normal user 1
        self.user1 = User.objects.create_user(
            email='user1@hive.com',
            password='User1Password123!',
            first_name='User',
            last_name='One',
            username='userone',
            is_verified=True
        )

        # Normal user 2
        self.user2 = User.objects.create_user(
            email='user2@hive.com',
            password='User2Password123!',
            first_name='User',
            last_name='Two',
            username='usertwo',
            is_verified=True
        )

    # 1. Admin Dashboard Authorization & Role Escalation Checks
    def test_normal_user_cannot_access_admin_dashboard(self):
        self.client.login(email='user1@hive.com', password='User1Password123!')
        res = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertRedirects(res, reverse('admin_dashboard:admin_login'))

    def test_admin_cannot_promote_self_or_others_to_superuser(self):
        self.client.login(email='adminstaff@hive.com', password='StaffPassword123!')
        res = self.client.post(reverse('admin_dashboard:role_update', kwargs={'pk': self.user1.pk}), {'role': 'SUPER_ADMIN'}, follow=True)
        self.user1.refresh_from_db()
        self.assertFalse(self.user1.is_superuser)

    def test_admin_cannot_assign_super_admin_role_directly(self):
        self.client.login(email='superadmin@hive.com', password='SuperPassword123!')
        res = self.client.post(reverse('admin_dashboard:admin_create'), {
            'user_id': self.user1.pk,
            'role': AdminProfile.Role.SUPER_ADMIN
        }, follow=True)
        self.assertContains(res, "Super Admin role cannot be assigned.")

    # 2. Object-Level Authorization (IDOR) Checks
    def test_user_cannot_delete_other_user_post(self):
        post = Post.objects.create(author=self.user1, content="User 1 Post")
        self.client.login(email='user2@hive.com', password='User2Password123!')
        res = self.client.post(reverse('posts:delete', kwargs={'pk': post.pk}))
        self.assertEqual(res.status_code, 404)
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())

    def test_user_cannot_delete_other_user_project(self):
        project = Project.objects.create(owner=self.user1, title="User 1 Project", short_description="Desc", description="Desc")
        self.client.login(email='user2@hive.com', password='User2Password123!')
        res = self.client.post(reverse('portfolio:project_delete', kwargs={'pk': project.pk}))
        self.assertEqual(res.status_code, 404)
        self.assertTrue(Project.objects.filter(pk=project.pk).exists())

    def test_user_cannot_delete_other_user_opportunity(self):
        op = Collaboration.objects.create(creator=self.user1, title="User 1 Opportunity", description="Desc", category="Dev")
        self.client.login(email='user2@hive.com', password='User2Password123!')
        res = self.client.post(reverse('marketplace:collaboration_delete', kwargs={'pk': op.pk}))
        self.assertEqual(res.status_code, 404)
        self.assertTrue(Collaboration.objects.filter(pk=op.pk).exists())

    def test_user_cannot_access_unauthorized_chat_room(self):
        conv = Conversation.objects.create(user1=self.user1, user2=self.admin)
        self.client.login(email='user2@hive.com', password='User2Password123!')
        res = self.client.get(reverse('chat:chat_room', kwargs={'conversation_id': conv.id}))
        self.assertEqual(res.status_code, 403)

    # 3. File Upload Security Checks
    def test_file_upload_rejects_executable_files(self):
        fake_exe = SimpleUploadedFile("malicious.exe", b"MZexecutabledata", content_type="application/x-msdownload")
        with self.assertRaises(ValidationError):
            validate_uploaded_image(fake_exe)

    def test_file_upload_rejects_malicious_svg(self):
        svg_script = SimpleUploadedFile("danger.svg", b'<svg><script>alert("xss")</script></svg>', content_type="image/svg+xml")
        with self.assertRaises(ValidationError):
            validate_uploaded_image(svg_script)

    def test_file_upload_accepts_valid_image(self):
        img_io = io.BytesIO()
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(img_io, format='PNG')
        img_io.seek(0)
        valid_png = SimpleUploadedFile("valid.png", img_io.read(), content_type="image/png")
        # Should not raise validation error
        validate_uploaded_image(valid_png)
