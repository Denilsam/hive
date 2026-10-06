from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import EmailOTP
from apps.profiles.models import Profile, Education, Experience, UserSkill, Skill
from apps.posts.models import Post, Like, Comment, SavedPost
from apps.portfolio.models import Project
from apps.connections.models import Follow, ConnectionRequest, Connection
from apps.marketplace.models import Collaboration, CollaborationApplication
from apps.notifications.models import Notification

User = get_user_model()


class MobileApiPhase2BFinalAuditTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # User 1 (Main test user)
        self.user1_password = "SecurePassword123!"
        self.user1 = User.objects.create_user(
            email="user1@example.com",
            password=self.user1_password,
            first_name="User",
            last_name="One",
            account_type=User.AccountType.STUDENT,
            is_active=True,
            is_verified=True,
        )
        self.profile1, _ = Profile.objects.get_or_create(user=self.user1)
        self.profile1.headline = "Developer"
        self.profile1.save()

        # User 2 (Second test user for permission checks)
        self.user2_password = "SecurePassword123!"
        self.user2 = User.objects.create_user(
            email="user2@example.com",
            password=self.user2_password,
            first_name="User",
            last_name="Two",
            account_type=User.AccountType.CREATOR,
            is_active=True,
            is_verified=True,
        )
        self.profile2, _ = Profile.objects.get_or_create(user=self.user2)
        self.profile2.headline = "Designer"
        self.profile2.save()

        # Tokens
        self.refresh1 = RefreshToken.for_user(self.user1)
        self.access1 = str(self.refresh1.access_token)

        self.refresh2 = RefreshToken.for_user(self.user2)
        self.access2 = str(self.refresh2.access_token)

    def auth_client(self, token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return client

    # --- Profile API Tests ---
    def test_get_my_profile(self):
        client = self.auth_client(self.access1)
        url = reverse('api:profile_me')
        response = client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['email'], 'user1@example.com')
        self.assertEqual(response.data['headline'], 'Developer')

    def test_patch_my_profile(self):
        client = self.auth_client(self.access1)
        url = reverse('api:profile_me')
        payload = {'headline': 'Senior Software Engineer', 'location': 'New York'}
        response = client.patch(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.profile1.refresh_from_db()
        self.assertEqual(self.profile1.headline, 'Senior Software Engineer')
        self.assertEqual(self.profile1.location, 'New York')

    def test_get_user_profile_detail_public(self):
        """Public profile view accessible without authentication."""
        anon_client = APIClient()
        url = reverse('api:profile_detail', kwargs={'user_id': self.user2.id})
        response = anon_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user']['email'], 'user2@example.com')
        self.assertEqual(response.data['headline'], 'Designer')

    def test_cannot_update_another_profile_via_me(self):
        client = self.auth_client(self.access1)
        url = reverse('api:profile_me')
        payload = {'headline': 'Hacked Headline'}
        client.patch(url, payload, format='json')

        self.profile2.refresh_from_db()
        self.assertEqual(self.profile2.headline, 'Designer')

    # --- Posts API Tests ---
    def test_create_post_text(self):
        client = self.auth_client(self.access1)
        url = reverse('api:posts_list_create')
        payload = {'content': 'Hello mobile world!', 'post_type': 'TEXT', 'visibility': 'PUBLIC'}
        response = client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'Hello mobile world!')
        self.assertEqual(response.data['author']['email'], 'user1@example.com')

    def test_create_post_with_media(self):
        from io import BytesIO
        from PIL import Image
        file_obj = BytesIO()
        img = Image.new('RGB', (10, 10), 'red')
        img.save(file_obj, 'jpeg')
        file_obj.seek(0)
        image = SimpleUploadedFile('test.jpg', file_obj.read(), content_type='image/jpeg')

        client = self.auth_client(self.access1)
        url = reverse('api:posts_list_create')
        response = client.post(url, {'content': 'Post with image', 'image': image}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIsNotNone(response.data['image_url'])

    def test_get_posts_feed_public_access(self):
        """Unauthenticated clients can view public feed."""
        Post.objects.create(author=self.user1, content='Public post', visibility='PUBLIC')
        anon_client = APIClient()
        url = reverse('api:posts_list_create')
        response = anon_client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_post_edit_and_delete_permissions(self):
        post = Post.objects.create(author=self.user1, content='User1 Post')

        # User2 tries to edit User1's post -> HTTP 403 Forbidden
        client2 = self.auth_client(self.access2)
        url = reverse('api:post_detail', kwargs={'post_id': post.id})
        response = client2.patch(url, {'content': 'Hacked'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # User2 tries to delete User1's post -> HTTP 403 Forbidden
        response = client2.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # User1 edits own post -> Success
        client1 = self.auth_client(self.access1)
        response = client1.patch(url, {'content': 'Updated by User1'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        post.refresh_from_db()
        self.assertEqual(post.content, 'Updated by User1')

    def test_post_like_and_save_toggle(self):
        post = Post.objects.create(author=self.user2, content='User2 Post')
        client1 = self.auth_client(self.access1)

        # Like
        like_url = reverse('api:post_like', kwargs={'post_id': post.id})
        res1 = client1.post(like_url)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertTrue(res1.data['is_liked'])

        # Unlike
        res2 = client1.post(like_url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertFalse(res2.data['is_liked'])

        # Save
        save_url = reverse('api:post_save', kwargs={'post_id': post.id})
        res3 = client1.post(save_url)
        self.assertEqual(res3.status_code, status.HTTP_200_OK)
        self.assertTrue(res3.data['is_saved'])

    def test_post_comments(self):
        post = Post.objects.create(author=self.user2, content='Commentable Post')
        client1 = self.auth_client(self.access1)

        comment_url = reverse('api:post_comments', kwargs={'post_id': post.id})
        res1 = client1.post(comment_url, {'content': 'Great post!'}, format='json')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        res2 = client1.get(comment_url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res2.data['results']), 1)

    # --- Opportunities API Tests ---
    def test_opportunities_listing_public(self):
        opp = Collaboration.objects.create(
            creator=self.user2,
            title='Flutter Developer Role',
            description='Build mobile UI',
            category='Mobile',
            status='OPEN'
        )
        anon_client = APIClient()
        url = reverse('api:opportunities_list_create')
        res = anon_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data['results']), 1)
        self.assertEqual(res.data['results'][0]['title'], 'Flutter Developer Role')

    def test_opportunity_detail_public(self):
        opp = Collaboration.objects.create(
            creator=self.user2,
            title='UI Designer Opportunity',
            description='Figma expert needed',
            category='Design',
            status='OPEN'
        )
        anon_client = APIClient()
        url = reverse('api:opportunities_detail', kwargs={'id': opp.id})
        res = anon_client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['title'], 'UI Designer Opportunity')

    def test_opportunity_application_and_duplicate_prevention(self):
        opp = Collaboration.objects.create(
            creator=self.user2,
            title='Backend Engineer Opportunity',
            description='Django specialist',
            category='Web',
            status='OPEN'
        )
        client1 = self.auth_client(self.access1)

        # Apply
        apply_url = reverse('api:opportunities_apply', kwargs={'id': opp.id})
        res1 = client1.post(apply_url, {'message': 'Interested in Backend role!'}, format='json')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Duplicate application attempt -> HTTP 400 Bad Request
        res2 = client1.post(apply_url, {'message': 'Duplicate application'}, format='json')
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already applied", res2.data['detail'])

        # Application ownership check
        my_apps_url = reverse('api:opportunities_my_applications')
        res_apps = client1.get(my_apps_url)
        self.assertEqual(res_apps.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_apps.data['results']), 1)
        self.assertEqual(res_apps.data['results'][0]['applicant']['email'], 'user1@example.com')

    def test_creator_cannot_apply_to_own_opportunity(self):
        opp = Collaboration.objects.create(
            creator=self.user1,
            title='Own Opportunity',
            description='Self opportunity',
            category='Tech',
            status='OPEN'
        )
        client1 = self.auth_client(self.access1)
        apply_url = reverse('api:opportunities_apply', kwargs={'id': opp.id})
        res = client1.post(apply_url, {'message': 'Applying to my own'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Notifications API Tests ---
    def test_notifications_list_and_read(self):
        n1 = Notification.objects.create(receiver=self.user1, sender=self.user2, notification_type='LIKE', message='User2 liked your post.')

        client1 = self.auth_client(self.access1)
        url_list = reverse('api:notifications_list')

        res1 = client1.get(url_list)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)
        self.assertEqual(res1.data['unread_count'], 1)

        mark_url = reverse('api:notification_mark_read', kwargs={'id': n1.id})
        res2 = client1.post(mark_url)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        n1.refresh_from_db()
        self.assertTrue(n1.is_read)

    def test_cannot_access_other_users_notifications(self):
        n2 = Notification.objects.create(receiver=self.user2, sender=self.user1, notification_type='LIKE', message='Private to User2')
        client1 = self.auth_client(self.access1)
        mark_url = reverse('api:notification_mark_read', kwargs={'id': n2.id})
        response = client1.post(mark_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_actions_require_auth(self):
        anon_client = APIClient()
        self.assertEqual(anon_client.get(reverse('api:profile_me')).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(anon_client.post(reverse('api:posts_list_create'), {'content': 'Anon'}).status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(anon_client.get(reverse('api:notifications_list')).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_website_session_login_regression(self):
        from django.test import Client
        web_client = Client()
        response = web_client.post(reverse('accounts:login'), {
            'email': 'user1@example.com',
            'password': self.user1_password
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
