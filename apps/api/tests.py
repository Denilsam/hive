from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models import EmailOTP, User

User = get_user_model()


class MobileAuthApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('api:auth_register')
        self.token_url = reverse('api:auth_token_obtain')
        self.refresh_url = reverse('api:auth_token_refresh')
        self.me_url = reverse('api:auth_me')
        self.otp_verify_url = reverse('api:auth_otp_verify')

        self.user_password = "SecurePassword123!"
        self.user = User.objects.create_user(
            email="existing.user@example.com",
            password=self.user_password,
            first_name="Jane",
            last_name="Doe",
            account_type=User.AccountType.STUDENT,
            is_active=True,
            is_verified=True,
        )

    @override_settings(ENABLE_EMAIL_OTP=False)
    def test_valid_mobile_registration_otp_disabled(self):
        """Test successful registration when OTP is disabled."""
        payload = {
            "first_name": "John",
            "last_name": "Smith",
            "email": "JOHN.SMITH@EXAMPLE.COM",
            "account_type": "student",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertFalse(response.data["requires_otp"])

        # Check normalized email in DB
        created_user = User.objects.get(email="john.smith@example.com")
        self.assertEqual(created_user.first_name, "John")
        self.assertTrue(created_user.is_verified)

    @override_settings(ENABLE_EMAIL_OTP=True)
    def test_valid_mobile_registration_otp_enabled(self):
        """Test registration when OTP is enabled creates unverified user and requests OTP."""
        payload = {
            "first_name": "Alice",
            "last_name": "Wonder",
            "email": "alice@example.com",
            "account_type": "creator",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["requires_otp"])
        self.assertEqual(response.data["email"], "alice@example.com")

        created_user = User.objects.get(email="alice@example.com")
        self.assertFalse(created_user.is_verified)
        self.assertFalse(created_user.is_active)

    def test_invalid_registration_password_mismatch(self):
        """Test registration fails when password and confirm_password do not match."""
        payload = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "mismatch@example.com",
            "account_type": "student",
            "password": "Password123!",
            "confirm_password": "DifferentPassword123!"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("confirm_password", response.data)

    def test_invalid_registration_weak_password(self):
        """Test registration fails with weak password violating Django validators."""
        payload = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "weakpass@example.com",
            "account_type": "student",
            "password": "123",
            "confirm_password": "123"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)

    def test_invalid_registration_existing_email(self):
        """Test registration fails when email is already registered."""
        payload = {
            "first_name": "Duplicate",
            "last_name": "User",
            "email": "EXISTING.USER@EXAMPLE.COM",
            "account_type": "freelancer",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)

    def test_invalid_registration_unauthorized_account_type(self):
        """Test registration fails when trying to register as admin or organization."""
        payload = {
            "first_name": "Hacker",
            "last_name": "Man",
            "email": "hacker@example.com",
            "account_type": "admin",
            "password": "StrongPassword123!",
            "confirm_password": "StrongPassword123!"
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("account_type", response.data)

    def test_mobile_login_email_password_success(self):
        """Test login with email and password returns JWT tokens and user data."""
        payload = {
            "email": "EXISTING.USER@EXAMPLE.COM",
            "password": self.user_password
        }
        response = self.client.post(self.token_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["email"], "existing.user@example.com")
        self.assertEqual(response.data["user"]["full_name"], "Jane Doe")

    def test_mobile_login_invalid_credentials(self):
        """Test login fails with incorrect password."""
        payload = {
            "email": "existing.user@example.com",
            "password": "WrongPassword123!"
        }
        response = self.client.post(self.token_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)

    def test_jwt_refresh_token(self):
        """Test obtaining a new access token using a valid refresh token."""
        refresh = RefreshToken.for_user(self.user)
        payload = {
            "refresh": str(refresh)
        }
        response = self.client.post(self.refresh_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

    def test_get_current_user_me_authenticated(self):
        """Test GET /api/v1/auth/me/ with valid Bearer token."""
        refresh = RefreshToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "existing.user@example.com")
        self.assertEqual(response.data["account_type"], "STUDENT")

    def test_get_current_user_me_unauthorized(self):
        """Test GET /api/v1/auth/me/ without authorization token fails with 401."""
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(ENABLE_EMAIL_OTP=True)
    def test_otp_verification_flow(self):
        """Test OTP code verification for an unverified user."""
        unverified = User.objects.create_user(
            email="otpuser@example.com",
            password="StrongPassword123!",
            first_name="Otp",
            last_name="Tester",
            account_type=User.AccountType.STUDENT,
            is_active=False,
            is_verified=False
        )
        raw_otp, otp_obj = EmailOTP.generate_otp_for_user(unverified)

        payload = {
            "email": "otpuser@example.com",
            "otp": raw_otp
        }
        response = self.client.post(self.otp_verify_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

        unverified.refresh_from_db()
        self.assertTrue(unverified.is_verified)
        self.assertTrue(unverified.is_active)

    def test_website_session_login_regression(self):
        """Regression test ensuring existing website session login is completely unaffected."""
        from django.test import Client
        web_client = Client()
        web_login_url = reverse('accounts:login')
        response = web_client.post(web_login_url, {
            'email': 'existing.user@example.com',
            'password': self.user_password
        }, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['user'].is_authenticated)
        self.assertEqual(response.context['user'].email, 'existing.user@example.com')
