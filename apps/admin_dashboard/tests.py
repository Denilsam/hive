import datetime
from django.utils import timezone
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.admin_dashboard.models import AdminProfile, AdminPermission, Report, PlatformSettings

User = get_user_model()

class AdminDashboardTests(TestCase):
    def setUp(self):
        self.super_user = User.objects.create_superuser(
            email='admin@connect.com',
            password='password123',
            first_name='Super',
            last_name='Admin'
        )
        self.normal_user = User.objects.create_user(
            email='user@connect.com',
            password='password123',
            first_name='Normal',
            last_name='User'
        )

    def test_admin_profile_auto_creation_for_superuser(self):
        self.client.login(email='admin@connect.com', password='password123')
        response = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_normal_user_access_denied(self):
        self.client.login(email='user@connect.com', password='password123')
        response = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertRedirects(response, reverse('admin_dashboard:admin_login'), fetch_redirect_response=False)

    def test_platform_settings_singleton(self):
        s1 = PlatformSettings.load()
        s2 = PlatformSettings.load()
        self.assertEqual(s1.pk, s2.pk)

    def test_role_management_promotion_and_demotion(self):
        # 1. Superadmin accesses Manage Roles page
        self.client.login(email='admin@connect.com', password='password123')
        role_list_url = reverse('admin_dashboard:role_list')
        response = self.client.get(role_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manage Roles")
        self.assertContains(response, "Normal User")

        # 2. Superadmin promotes normal user to ADMIN
        update_url = reverse('admin_dashboard:role_update', kwargs={'pk': self.normal_user.pk})
        res_promote = self.client.post(update_url, {'role': 'ADMIN'}, fetch_redirect_response=False)
        self.assertRedirects(res_promote, role_list_url, fetch_redirect_response=False)

        # Verify database state for promoted admin
        self.normal_user.refresh_from_db()
        self.assertTrue(self.normal_user.is_staff)
        self.assertFalse(self.normal_user.is_superuser)
        self.assertEqual(self.normal_user.account_type, 'ADMIN')

        # 3. Promoted Admin logs in and accesses Admin Dashboard
        self.client.login(email='user@connect.com', password='password123')
        res_dash = self.client.get(reverse('admin_dashboard:dashboard'))
        self.assertEqual(res_dash.status_code, 200)

        # 4. Promoted Admin attempts to access Manage Roles -> 302/Redirect/403 (Denied)
        res_role_denied = self.client.get(role_list_url)
        self.assertRedirects(res_role_denied, reverse('admin_dashboard:dashboard'), fetch_redirect_response=False)

        # 5. Promoted Admin attempts to POST role update -> Denied
        res_update_denied = self.client.post(update_url, {'role': 'USER'})
        self.assertRedirects(res_update_denied, reverse('admin_dashboard:dashboard'), fetch_redirect_response=False)

        # 6. Superadmin demotes Admin back to USER
        self.client.login(email='admin@connect.com', password='password123')
        res_demote = self.client.post(update_url, {'role': 'USER'})
        self.assertRedirects(res_demote, role_list_url, fetch_redirect_response=False)

        self.normal_user.refresh_from_db()
        self.assertFalse(self.normal_user.is_staff)
        self.assertFalse(self.normal_user.is_superuser)

        # 7. Superadmin protection: Superadmin cannot be modified via role update
        su_update_url = reverse('admin_dashboard:role_update', kwargs={'pk': self.super_user.pk})
        res_su_update = self.client.post(su_update_url, {'role': 'USER'})
        self.assertRedirects(res_su_update, role_list_url, fetch_redirect_response=False)
        self.super_user.refresh_from_db()
        self.assertTrue(self.super_user.is_superuser)

    def test_superadmin_can_delete_another_superadmin_when_multiple_exist(self):
        # Create second Superadmin (Superadmin B)
        super_user_b = User.objects.create_superuser(
            email='admin_b@connect.com',
            password='password123',
            first_name='Super',
            last_name='Admin B'
        )

        self.assertEqual(User.objects.filter(is_superuser=True).count(), 2)

        # 1. Login as Superadmin A and delete Superadmin B -> Success
        self.client.login(email='admin@connect.com', password='password123')
        delete_b_url = reverse('admin_dashboard:user_permanent_delete', kwargs={'pk': super_user_b.pk})
        res_delete_b = self.client.post(delete_b_url, fetch_redirect_response=False)
        self.assertRedirects(res_delete_b, reverse('admin_dashboard:user_list'), fetch_redirect_response=False)
        
        # Superadmin B is deleted, count becomes 1
        self.assertFalse(User.objects.filter(pk=super_user_b.pk).exists())
        self.assertEqual(User.objects.filter(is_superuser=True).count(), 1)

        # 2. Superadmin A attempts to delete self -> Blocked (cannot delete self)
        delete_a_url = reverse('admin_dashboard:user_permanent_delete', kwargs={'pk': self.super_user.pk})
        res_delete_a_self = self.client.post(delete_a_url, fetch_redirect_response=False)
        self.assertRedirects(res_delete_a_self, reverse('admin_dashboard:user_detail', kwargs={'pk': self.super_user.pk}), fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(pk=self.super_user.pk).exists())

        # 3. If another superadmin exists, attempt to delete the last remaining superadmin -> Blocked
        super_user_c = User.objects.create_superuser(
            email='admin_c@connect.com',
            password='password123',
            first_name='Super',
            last_name='Admin C'
        )
        self.client.login(email='admin_c@connect.com', password='password123')
        # Admin C deletes Admin A -> Success (count becomes 1)
        self.client.post(reverse('admin_dashboard:user_permanent_delete', kwargs={'pk': self.super_user.pk}), fetch_redirect_response=False)
        self.assertEqual(User.objects.filter(is_superuser=True).count(), 1)

        # Now only Admin C remains. Non-superuser or target attempts to delete C -> Blocked
        res_last = self.client.post(reverse('admin_dashboard:user_permanent_delete', kwargs={'pk': super_user_c.pk}), fetch_redirect_response=False)
        self.assertRedirects(res_last, reverse('admin_dashboard:user_detail', kwargs={'pk': super_user_c.pk}), fetch_redirect_response=False)
        self.assertEqual(User.objects.filter(is_superuser=True).count(), 1)

    def test_branding_settings_access_and_permissions(self):
        settings_url = reverse('admin_dashboard:settings')
        
        # 1. Normal user access denied
        self.client.login(email='user@connect.com', password='password123')
        res_denied = self.client.get(settings_url)
        self.assertRedirects(res_denied, reverse('admin_dashboard:dashboard'), fetch_redirect_response=False)

        # 2. Superadmin access allowed
        self.client.login(email='admin@connect.com', password='password123')
        res_allowed = self.client.get(settings_url)
        self.assertEqual(res_allowed.status_code, 200)
        self.assertContains(res_allowed, "Platform & Branding Settings")
        self.assertContains(res_allowed, "Primary Logo")

    def test_branding_logo_upload_and_validation(self):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.login(email='admin@connect.com', password='password123')
        settings_url = reverse('admin_dashboard:settings')

        # 1. Test uploading valid PNG logo
        file_obj = io.BytesIO()
        img = Image.new('RGB', (100, 100), color=(0, 255, 0))
        img.save(file_obj, 'PNG')
        file_obj.seek(0)
        valid_logo = SimpleUploadedFile('test_logo.png', file_obj.read(), content_type='image/png')

        post_data = {
            'site_name': 'Hive Enterprise',
            'contact_email': 'support@hive.com',
            'default_profile_visibility': 'PUBLIC',
            'logo': valid_logo,
        }
        res_upload = self.client.post(settings_url, post_data, follow=True)
        self.assertEqual(res_upload.status_code, 200)

        s = PlatformSettings.load()
        self.assertEqual(s.site_name, 'Hive Enterprise')
        self.assertTrue(s.logo)
        self.assertIn('test_logo', s.logo.name)

        # 2. Test rejecting invalid file type (e.g. txt file disguised as image)
        invalid_file = SimpleUploadedFile('evil.txt', b'<?php echo 1; ?>', content_type='text/plain')
        res_invalid = self.client.post(settings_url, {
            'site_name': 'Hive Enterprise',
            'contact_email': 'support@hive.com',
            'default_profile_visibility': 'PUBLIC',
            'logo': invalid_file,
        }, follow=True)
        self.assertContains(res_invalid, "Upload a valid image")

        # 3. Test rejecting oversized file (>2MB)
        large_bytes = b'0' * (2 * 1024 * 1024 + 100)
        large_file = SimpleUploadedFile('large.png', large_bytes, content_type='image/png')
        res_large = self.client.post(settings_url, {
            'site_name': 'Hive Enterprise',
            'contact_email': 'support@hive.com',
            'default_profile_visibility': 'PUBLIC',
            'logo': large_file,
        }, follow=True)
        self.assertContains(res_large, "File size exceeds maximum limit of 2 MB.")

    def test_branding_global_context_and_reset(self):
        import io
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile

        self.client.login(email='admin@connect.com', password='password123')
        settings_url = reverse('admin_dashboard:settings')

        # 1. Verify fallback defaults when no custom logo is uploaded
        s = PlatformSettings.load()
        s.logo = None
        s.favicon = None
        s.admin_logo = None
        s.save()

        self.client.logout()
        res_home = self.client.get(reverse('accounts:login'))
        self.assertEqual(res_home.status_code, 200)
        self.assertContains(res_home, "/static/images/branding/hive_logo.svg")

        # Log back in for admin actions
        self.client.login(email='admin@connect.com', password='password123')

        # 2. Upload custom logo and favicon
        file_obj = io.BytesIO()
        img = Image.new('RGB', (64, 64), color=(255, 0, 0))
        img.save(file_obj, 'PNG')
        file_obj.seek(0)
        custom_logo = SimpleUploadedFile('custom_logo.png', file_obj.read(), content_type='image/png')

        fav_obj = io.BytesIO()
        fav_img = Image.new('RGB', (32, 32), color=(0, 0, 255))
        fav_img.save(fav_obj, 'PNG')
        fav_obj.seek(0)
        custom_fav = SimpleUploadedFile('custom_fav.png', fav_obj.read(), content_type='image/png')

        self.client.post(settings_url, {
            'site_name': 'Custom Hive',
            'contact_email': 'support@hive.com',
            'default_profile_visibility': 'PUBLIC',
            'logo': custom_logo,
            'favicon': custom_fav,
        })

        s.refresh_from_db()
        self.assertTrue(s.logo)
        self.assertTrue(s.favicon)

        # 3. Test Reset Logo action
        res_reset = self.client.post(settings_url, {'action': 'reset_logo'}, follow=True)
        self.assertContains(res_reset, "Primary logo reset to default.")

        s.refresh_from_db()
        self.assertFalse(s.logo)
        self.assertEqual(s.logo_url, '/static/images/branding/hive_logo.svg')


from django.core import mail
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from unittest.mock import patch

class AdminPasswordResetTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Superadmin user
        self.super_admin = User.objects.create_superuser(
            email='superadmin@hive.com',
            password='OldSuperPassword123!',
            first_name='Super',
            last_name='Admin'
        )
        AdminProfile.objects.get_or_create(
            user=self.super_admin,
            defaults={'role': AdminProfile.Role.SUPER_ADMIN, 'is_active': True}
        )

        # Admin user
        self.admin = User.objects.create_user(
            email='adminstaff@hive.com',
            password='OldStaffPassword123!',
            first_name='Staff',
            last_name='Admin',
            is_staff=True
        )
        AdminProfile.objects.get_or_create(
            user=self.admin,
            defaults={'role': AdminProfile.Role.CONTENT_MODERATOR, 'is_active': True}
        )

        # Normal user
        self.normal_user = User.objects.create_user(
            email='normaluser@hive.com',
            password='NormalUserPassword123!',
            first_name='Normal',
            last_name='User'
        )

    def test_admin_forgot_password_get(self):
        url = reverse('admin_dashboard:admin_forgot_password')
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Forgot Admin Password?")
        self.assertContains(res, "Send Reset Link")
        self.assertContains(res, "Back to Admin Login")

    def test_admin_password_reset_request_for_superuser(self):
        url = reverse('admin_dashboard:admin_forgot_password')
        res = self.client.post(url, {'email': 'superadmin@hive.com'}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "If an eligible admin account exists for this email, a password reset link has been sent.")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['superadmin@hive.com'])
        self.assertIn("Hive Admin Password Reset", mail.outbox[0].subject)
        self.assertIn("reset-password/", mail.outbox[0].body)

    def test_admin_password_reset_request_for_admin_staff(self):
        url = reverse('admin_dashboard:admin_forgot_password')
        res = self.client.post(url, {'email': 'adminstaff@hive.com'}, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "If an eligible admin account exists for this email, a password reset link has been sent.")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['adminstaff@hive.com'])

    def test_admin_password_reset_request_for_normal_user_enumeration_protection(self):
        url = reverse('admin_dashboard:admin_forgot_password')
        res = self.client.post(url, {'email': 'normaluser@hive.com'}, follow=True)
        self.assertEqual(res.status_code, 200)
        # Identical response text
        self.assertContains(res, "If an eligible admin account exists for this email, a password reset link has been sent.")
        # Crucial: NO email is sent to normal users via Admin Reset
        self.assertEqual(len(mail.outbox), 0)

    def test_admin_password_reset_request_for_nonexistent_email_enumeration_protection(self):
        url = reverse('admin_dashboard:admin_forgot_password')
        res = self.client.post(url, {'email': 'nobody@hive.com'}, follow=True)
        self.assertEqual(res.status_code, 200)
        # Identical response text
        self.assertContains(res, "If an eligible admin account exists for this email, a password reset link has been sent.")
        self.assertEqual(len(mail.outbox), 0)

    def test_admin_password_reset_confirm_get_valid_token(self):
        token = default_token_generator.make_token(self.super_admin)
        uidb64 = urlsafe_base64_encode(force_bytes(self.super_admin.pk))
        url = reverse('admin_dashboard:admin_password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})

        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Reset Admin Password")
        self.assertContains(res, "New Password")

    def test_admin_password_reset_confirm_get_invalid_token(self):
        uidb64 = urlsafe_base64_encode(force_bytes(self.super_admin.pk))
        url = reverse('admin_dashboard:admin_password_reset_confirm', kwargs={'uidb64': uidb64, 'token': 'invalid-token'})

        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Invalid or Expired Link")

    def test_admin_password_reset_confirm_get_expired_token(self):
        token = default_token_generator.make_token(self.super_admin)
        uidb64 = urlsafe_base64_encode(force_bytes(self.super_admin.pk))
        url = reverse('admin_dashboard:admin_password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})

        with patch('django.contrib.auth.tokens.default_token_generator.check_token', return_value=False):
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200)
            self.assertContains(res, "Invalid or Expired Link")

    def test_admin_password_reset_confirm_post_password_mismatch(self):
        token = default_token_generator.make_token(self.super_admin)
        uidb64 = urlsafe_base64_encode(force_bytes(self.super_admin.pk))
        url = reverse('admin_dashboard:admin_password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})

        res = self.client.post(url, {
            'password1': 'NewValidPassword123!',
            'password2': 'MismatchPassword123!'
        }, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Passwords do not match")

    def test_admin_password_reset_confirm_post_weak_password(self):
        token = default_token_generator.make_token(self.super_admin)
        uidb64 = urlsafe_base64_encode(force_bytes(self.super_admin.pk))
        url = reverse('admin_dashboard:admin_password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})

        res = self.client.post(url, {
            'password1': '123',
            'password2': '123'
        }, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "too short")

    def test_admin_password_reset_complete_flow(self):
        # 1. Generate token
        token = default_token_generator.make_token(self.super_admin)
        uidb64 = urlsafe_base64_encode(force_bytes(self.super_admin.pk))
        url = reverse('admin_dashboard:admin_password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})

        # 2. Reset password
        new_password = 'BrandNewSuperPassword123!'
        res = self.client.post(url, {
            'password1': new_password,
            'password2': new_password
        }, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Password Reset Complete")

        # 3. Old password no longer works
        old_login_res = self.client.post(reverse('admin_dashboard:admin_login'), {
            'email': 'superadmin@hive.com',
            'password': 'OldSuperPassword123!'
        })
        self.assertContains(old_login_res, "Invalid admin credentials")

        # 4. New password works
        new_login_res = self.client.post(reverse('admin_dashboard:admin_login'), {
            'email': 'superadmin@hive.com',
            'password': new_password
        }, follow=True)
        self.assertEqual(new_login_res.status_code, 200)
        self.assertContains(new_login_res, "Superadmin Dashboard")

        # 5. Token is single-use and cannot be reused
        reuse_res = self.client.get(url)
        self.assertContains(reuse_res, "Invalid or Expired Link")

    def test_roles_and_permissions_remain_unchanged(self):
        # Verify superadmin and staff flags remain unchanged after reset
        token = default_token_generator.make_token(self.super_admin)
        uidb64 = urlsafe_base64_encode(force_bytes(self.super_admin.pk))
        url = reverse('admin_dashboard:admin_password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})

        self.client.post(url, {
            'password1': 'ResetSuperPassword123!',
            'password2': 'ResetSuperPassword123!'
        })

        self.super_admin.refresh_from_db()
        self.assertTrue(self.super_admin.is_superuser)
        self.assertTrue(self.super_admin.is_staff)
        self.assertEqual(self.super_admin.admin_profile.role, AdminProfile.Role.SUPER_ADMIN)



