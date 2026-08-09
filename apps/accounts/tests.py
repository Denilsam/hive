from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from unittest.mock import MagicMock

from apps.accounts.tokens import email_verification_token
from apps.accounts.adapters import CustomSocialAccountAdapter

User = get_user_model()


class AuthenticationSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.register_url = reverse('accounts:register')
        self.login_url = reverse('accounts:login')
        self.logout_url = reverse('accounts:logout')
        self.forgot_password_url = reverse('accounts:forgot_password')
        self.select_account_type_url = reverse('accounts:select_account_type')
        
        self.user_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'test@example.com',
            'account_type': 'STUDENT',
            'password': 'StrongPassword123!',
            'confirm_password': 'StrongPassword123!'
        }

    def test_registration_flow(self):
        # Test valid registration
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, 302)
        
        # Check user created inactive and unverified
        user = User.objects.get(email='test@example.com')
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_verified)
        
        # Check verification OTP email sent with 6-digit code
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Verify your Hive account", mail.outbox[0].subject)
        self.assertIn("Your verification code is:", mail.outbox[0].body)
        
    def test_duplicate_email_registration_blocked(self):
        # Create initial user
        User.objects.create_user(email='test@example.com', password='Password123!', first_name='A', last_name='B')
        
        # Try registering again with same email
        response = self.client.post(self.register_url, self.user_data)
        self.assertEqual(response.status_code, 200)  # Form re-rendered
        self.assertIn("email", response.context['form'].errors)
        self.assertIn("A user with this email address already exists.", response.context['form'].errors['email'])

    def test_weak_password_validation(self):
        weak_data = self.user_data.copy()
        weak_data['password'] = '123'
        weak_data['confirm_password'] = '123'
        
        response = self.client.post(self.register_url, weak_data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)

    def test_email_otp_verification_works(self):
        from apps.accounts.models import EmailOTP
        import re

        # Register user
        self.client.post(self.register_url, self.user_data)
        user = User.objects.get(email='test@example.com')
        
        # Extract OTP from sent email
        body = mail.outbox[0].body
        match = re.search(r'Your verification code is:\s*(\d{6})', body)
        self.assertIsNotNone(match)
        raw_otp = match.group(1)

        # Submit OTP to pending page
        session = self.client.session
        session['unverified_user_email'] = user.email
        session.save()

        response = self.client.post(reverse('accounts:verify_email_pending'), {'otp': raw_otp})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.login_url)

        # Verify user is active and verified
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_verified)

        # Ensure OTP record is marked used
        otp_rec = EmailOTP.objects.filter(user=user).last()
        self.assertTrue(otp_rec.is_used)

    def test_wrong_and_expired_otp(self):
        from apps.accounts.models import EmailOTP
        from django.utils import timezone
        from datetime import timedelta

        # Register user
        self.client.post(self.register_url, self.user_data)
        user = User.objects.get(email='test@example.com')

        session = self.client.session
        session['unverified_user_email'] = user.email
        session.save()

        # Submit wrong OTP -> Rejected
        response = self.client.post(reverse('accounts:verify_email_pending'), {'otp': '000000'}, follow=True)
        self.assertIn("Incorrect verification code.", response.content.decode('utf-8'))
        user.refresh_from_db()
        self.assertFalse(user.is_verified)

        # Expire the active OTP
        active_otp = EmailOTP.objects.filter(user=user, is_used=False).first()
        active_otp.expires_at = timezone.now() - timedelta(minutes=1)
        active_otp.save()

        # Submit correct OTP on expired record -> Rejected
        response_exp = self.client.post(reverse('accounts:verify_email_pending'), {'otp': '123456'}, follow=True)
        self.assertIn("expired", response_exp.content.decode('utf-8'))
        user.refresh_from_db()
        self.assertFalse(user.is_verified)

    def test_otp_attempt_limit(self):
        from apps.accounts.models import EmailOTP

        self.client.post(self.register_url, self.user_data)
        user = User.objects.get(email='test@example.com')

        session = self.client.session
        session['unverified_user_email'] = user.email
        session.save()

        # Submit wrong OTP 5 times
        for _ in range(5):
            self.client.post(reverse('accounts:verify_email_pending'), {'otp': '999999'})

        active_otp = EmailOTP.objects.filter(user=user).last()
        self.assertTrue(active_otp.is_used)

    def test_resend_otp_and_cooldown(self):
        self.client.post(self.register_url, self.user_data)
        user = User.objects.get(email='test@example.com')

        session = self.client.session
        session['unverified_user_email'] = user.email
        session.save()

        # Immediate resend within 60s -> Cooldown error
        response_cooldown = self.client.post(reverse('accounts:resend_verification'), follow=True)
        self.assertIn("Please wait", response_cooldown.content.decode('utf-8'))

    def test_login_verified_user(self):
        # Create a verified user
        user = User.objects.create_user(
            email='verified@example.com',
            password='StrongPassword123!',
            first_name='Verified',
            last_name='User',
            account_type='STUDENT',
            is_verified=True,
            is_active=True
        )
        
        response = self.client.post(self.login_url, {
            'email': 'verified@example.com',
            'password': 'StrongPassword123!'
        })
        self.assertEqual(response.status_code, 302)
        # User is logged in, and has account_type so they redirect to home
        self.assertRedirects(response, reverse('home'), target_status_code=302)

    def test_login_unverified_user_blocked(self):
        # Create an unverified user
        user = User.objects.create_user(
            email='unverified@example.com',
            password='StrongPassword123!',
            first_name='Unverified',
            last_name='User',
            account_type='STUDENT',
            is_verified=False,
            is_active=False
        )
        
        response = self.client.post(self.login_url, {
            'email': 'unverified@example.com',
            'password': 'StrongPassword123!'
        })
        self.assertEqual(response.status_code, 302)  # Redirects to OTP verification
        self.assertRedirects(response, reverse('accounts:verify_email_pending'))

    def test_login_redirect_select_account_type_if_missing(self):
        # Create user without account type
        user = User.objects.create_user(
            email='notype@example.com',
            password='StrongPassword123!',
            first_name='No',
            last_name='Type',
            account_type=None,
            is_verified=True,
            is_active=True
        )
        
        response = self.client.post(self.login_url, {
            'email': 'notype@example.com',
            'password': 'StrongPassword123!'
        })
        self.assertEqual(response.status_code, 302)
        # Should redirect to choose account type
        self.assertRedirects(response, reverse('accounts:select_account_type'))

    def test_password_reset_flow(self):
        # Create a verified user
        user = User.objects.create_user(
            email='reset@example.com',
            password='OldPassword123!',
            first_name='Reset',
            last_name='User',
            is_verified=True,
            is_active=True
        )
        
        # Submit forgot password form
        response = self.client.post(self.forgot_password_url, {'email': 'reset@example.com'})
        self.assertEqual(response.status_code, 302)
        
        # Check reset email sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Reset your Hive password", mail.outbox[0].subject)
        
        # Get reset details
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_confirm_url = reverse('accounts:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
        
        # Submit new password
        response = self.client.post(reset_confirm_url, {
            'password': 'NewPassword123!',
            'confirm_password': 'NewPassword123!'
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify password changed
        user.refresh_from_db()
        self.assertTrue(user.check_password('NewPassword123!'))

    def test_social_account_adapter_logic(self):
        adapter = CustomSocialAccountAdapter()
        user = User(email='social@example.com', first_name='Social', last_name='User')
        
        # Mock requests object
        request = MagicMock()
        request.user = user
        
        # With account_type missing, should redirect to select_account_type
        user.account_type = None
        self.assertEqual(adapter.get_login_redirect_url(request), reverse('accounts:select_account_type'))
        
        # With account_type present, should redirect to home
        user.account_type = 'STUDENT'
        self.assertEqual(adapter.get_login_redirect_url(request), reverse('home'))

    def test_user_creation_auto_generates_unique_username(self):
        # Create user without explicit username
        user1 = User.objects.create_user(email='alex@example.com', password='Password123!')
        self.assertEqual(user1.username, 'alex')

        # Create second user with same email prefix
        user2 = User.objects.create_user(email='alex@another.com', password='Password123!')
        self.assertEqual(user2.username, 'alex1')

    def test_google_signup_adapter_populates_username(self):
        adapter = CustomSocialAccountAdapter()
        user = User(email='googleuser@example.com', first_name='Google', last_name='User')
        sociallogin = MagicMock()
        sociallogin.user = user
        request = MagicMock()

        # Save user via adapter
        saved_user = adapter.save_user(request, sociallogin)
        self.assertEqual(saved_user.username, 'googleuser')
        self.assertTrue(saved_user.is_verified)

    def test_profile_detail_routing_with_missing_or_none_username(self):
        user = User.objects.create_user(email='routing@example.com', password='Password123!', is_active=True, is_verified=True)
        self.client.force_login(user)

        # Access profile detail with 'None' string
        response = self.client.get(reverse('profiles:profile_detail', kwargs={'username': 'None'}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['profile_user'], user)

    def test_superadmin_architecture_separation_and_security(self):
        # 1. Normal user creation creates Profile & appears in Network Discovery
        user1 = User.objects.create_user(
            email='member1@example.com',
            password='StrongPassword123!',
            first_name='Member',
            last_name='One',
            account_type='STUDENT',
            is_active=True,
            is_verified=True
        )
        user2 = User.objects.create_user(
            email='member2@example.com',
            password='StrongPassword123!',
            first_name='Member',
            last_name='Two',
            account_type='CREATOR',
            is_active=True,
            is_verified=True
        )
        self.assertTrue(hasattr(user1, 'profile') and user1.profile is not None)

        network_url = reverse('connections:network')
        self.client.force_login(user1)
        resp_network = self.client.get(network_url)
        self.assertIn(user2, resp_network.context['users'])

        # 2. Superadmin creation does NOT create Connect Profile & excluded from Network
        superuser = User.objects.create_superuser(
            email='superadmin@example.com',
            password='StrongPassword123!',
            first_name='Super',
            last_name='Admin'
        )
        self.assertFalse(hasattr(superuser, 'profile') and superuser.profile is not None)
        resp_network_su = self.client.get(network_url)
        self.assertNotIn(superuser, resp_network_su.context['users'])

        # 3. Security: Normal user blocked from admin dashboard
        dashboard_url = reverse('admin_dashboard:dashboard')
        resp_normal_admin = self.client.get(dashboard_url)
        self.assertEqual(resp_normal_admin.status_code, 302) # Redirected access denied

        # 4. Security: Superadmin access granted
        self.client.force_login(superuser)
        resp_su_admin = self.client.get(dashboard_url)
        self.assertEqual(resp_su_admin.status_code, 200)

        # 5. Total Users stat excludes superadmin count
        self.assertEqual(resp_su_admin.context['total_users'], User.objects.filter(is_superuser=False).count())

    def test_admin_delete_endpoints_security_and_functionality(self):
        superuser = User.objects.create_superuser(email='admin_del@connect.com', password='password123')
        normal_user = User.objects.create_user(email='user_del@connect.com', password='password123', is_active=True, is_verified=True)

        from apps.posts.models import Post
        from apps.portfolio.models import Project
        from apps.marketplace.models import Collaboration

        post = Post.objects.create(author=normal_user, content="Post to delete")
        project = Project.objects.create(owner=normal_user, title="Project to delete")
        collab = Collaboration.objects.create(creator=normal_user, title="Collab to delete")

        post_delete_url = reverse('admin_dashboard:post_delete', kwargs={'pk': post.pk})
        portfolio_delete_url = reverse('admin_dashboard:portfolio_delete', kwargs={'pk': project.pk})
        marketplace_delete_url = reverse('admin_dashboard:marketplace_delete', kwargs={'pk': collab.pk})

        # 1. GET requests must NOT delete records
        self.client.force_login(superuser)
        self.client.get(post_delete_url)
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())

        # 2. Normal user POST must be rejected (302 redirect to admin login) and NOT delete records
        self.client.force_login(normal_user)
        resp_norm = self.client.post(post_delete_url)
        self.assertEqual(resp_norm.status_code, 302)
        self.assertTrue(Post.objects.filter(pk=post.pk).exists())

        # 3. Superadmin POST deletes records successfully
        self.client.force_login(superuser)
        resp_post = self.client.post(post_delete_url)
        self.assertEqual(resp_post.status_code, 302)
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

        resp_proj = self.client.post(portfolio_delete_url)
        self.assertEqual(resp_proj.status_code, 302)
        self.assertFalse(Project.objects.filter(pk=project.pk).exists())

        resp_collab = self.client.post(marketplace_delete_url)
        self.assertEqual(resp_collab.status_code, 302)
        self.assertFalse(Collaboration.objects.filter(pk=collab.pk).exists())

        # 4. Superadmin self-delete protection
        user_delete_url = reverse('admin_dashboard:user_delete', kwargs={'pk': superuser.pk})
        resp_self = self.client.post(user_delete_url)
        self.assertEqual(resp_self.status_code, 302)
        superuser.refresh_from_db()
        self.assertTrue(superuser.is_active)

    def test_unauthenticated_protected_page_redirect_to_connect_login_with_next(self):
        # Access protected notifications page while logged out
        notif_url = reverse('notifications:notification_list')
        response = self.client.get(notif_url)
        self.assertEqual(response.status_code, 302)
        
        # Verify redirect goes to custom Connect login (/login/?next=/notifications/)
        login_url = reverse('accounts:login')
        self.assertRedirects(response, f"{login_url}?next={notif_url}", fetch_redirect_response=False)

        # Submit login form with next parameter
        user = User.objects.create_user(
            email='nexttest@example.com',
            password='StrongPassword123!',
            is_active=True,
            is_verified=True,
            account_type='STUDENT'
        )
        login_response = self.client.post(f"{login_url}?next={notif_url}", {
            'email': 'nexttest@example.com',
            'password': 'StrongPassword123!',
            'next': notif_url
        })
        self.assertRedirects(login_response, notif_url, fetch_redirect_response=False)

    def test_all_account_types_registration(self):
        account_types = ['STUDENT', 'CREATOR', 'FREELANCER', 'ORGANIZATION']
        for i, acc_type in enumerate(account_types):
            email = f"user_{acc_type.lower()}@example.com"
            data = {
                'first_name': 'Test',
                'last_name': 'User',
                'email': email,
                'account_type': acc_type,
                'password': 'StrongPassword123!',
                'confirm_password': 'StrongPassword123!'
            }
            response = self.client.post(self.register_url, data)
            self.assertEqual(response.status_code, 302, f"Failed for account_type {acc_type}")
            user = User.objects.get(email=email)
            self.assertEqual(user.account_type, acc_type)
            self.assertFalse(user.is_active)
            self.assertFalse(user.is_verified)

    def test_invalid_account_type_rejected(self):
        invalid_data = self.user_data.copy()
        invalid_data['email'] = 'invalid_acc@example.com'
        invalid_data['account_type'] = 'INVALID_TYPE'
        response = self.client.post(self.register_url, invalid_data)
        self.assertEqual(response.status_code, 200)
        self.assertIn('account_type', response.context['form'].errors)




