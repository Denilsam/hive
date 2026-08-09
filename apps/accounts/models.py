from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


class UserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifier
    for authentication instead of usernames.
    """
    def connect_members(self):
        """Returns non-superuser, active Connect members."""
        return self.get_queryset().filter(is_superuser=False, is_active=True)

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        
        # Auto-generate unique username from email if not provided or empty
        username = extra_fields.get('username')
        if not username:
            base_username = email.split('@')[0]
            username = base_username
            counter = 1
            while self.model.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            extra_fields['username'] = username

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        extra_fields.setdefault('account_type', 'ADMIN')

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class AccountType(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        CREATOR = 'CREATOR', 'Creator'
        FREELANCER = 'FREELANCER', 'Freelancer'
        ORGANIZATION = 'ORGANIZATION', 'Organization'
        ADMIN = 'ADMIN', 'Admin'

    # Make username optional and unique=False to support email-based auth
    username = models.CharField(max_length=150, unique=False, blank=True, null=True)
    email = models.EmailField(unique=True)
    
    # Account details
    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        blank=True,
        null=True,
    )
    is_verified = models.BooleanField(default=False)
    profile_completed = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    @property
    def is_connect_member(self):
        """Returns True if the user is an active, non-superuser Connect member."""
        return self.is_active and not self.is_superuser

    def save(self, *args, **kwargs):
        if not self.username:
            if self.email:
                base_username = self.email.split('@')[0]
            else:
                base_username = "user"
            username = base_username
            counter = 1
            User = self.__class__
            while User.objects.filter(username=username).exclude(pk=self.pk).exists():
                username = f"{base_username}{counter}"
                counter += 1
            self.username = username
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} ({self.get_account_type_display() if self.account_type else 'No Type'})"


class AuthLandingImage(models.Model):
    image = models.ImageField(upload_to='auth_landing/')
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'id']

    def __str__(self):
        return f"{self.title} (Active: {self.is_active})"


import hashlib
import secrets
from django.utils import timezone
from datetime import timedelta

class EmailOTP(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='email_otps'
    )
    otp_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempt_count = models.PositiveIntegerField(default=0)
    is_used = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    @staticmethod
    def hash_otp(raw_otp):
        return hashlib.sha256(raw_otp.encode('utf-8')).hexdigest()

    @classmethod
    def generate_otp_for_user(cls, user):
        # Invalidate previous unused OTPs for this user
        cls.objects.filter(user=user, is_used=False).update(is_used=True)

        # Generate cryptographically secure 6-digit numeric string
        raw_otp = f"{secrets.randbelow(1000000):06d}"
        otp_hash = cls.hash_otp(raw_otp)
        expires_at = timezone.now() + timedelta(minutes=10)

        otp_obj = cls.objects.create(
            user=user,
            otp_hash=otp_hash,
            expires_at=expires_at
        )
        return raw_otp, otp_obj

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at and self.attempt_count < 5

    def verify_otp(self, input_otp):
        if not self.is_valid():
            return False, "EXPIRED_OR_LIMITED"

        self.attempt_count += 1
        self.save(update_fields=['attempt_count'])

        if self.hash_otp(input_otp) == self.otp_hash:
            self.is_used = True
            self.save(update_fields=['is_used'])
            return True, "SUCCESS"
        
        if self.attempt_count >= 5:
            self.is_used = True
            self.save(update_fields=['is_used'])
            return False, "TOO_MANY_ATTEMPTS"

        return False, "INCORRECT"
