import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class AdminProfile(models.Model):
    class Role(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Admin'
        ADMIN_ASSISTANT = 'ADMIN_ASSISTANT', 'Admin Assistant'
        CONTENT_MODERATOR = 'CONTENT_MODERATOR', 'Content Moderator'
        SUPPORT_ADMIN = 'SUPPORT_ADMIN', 'Support Admin'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='admin_profile'
    )
    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.SUPPORT_ADMIN
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_admin_profiles'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.email} - {self.get_role_display()}"


class AdminPermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    codename = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.codename})"


class AdminUserPermission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_profile = models.ForeignKey(
        AdminProfile,
        on_delete=models.CASCADE,
        related_name='user_permissions'
    )
    permission = models.ForeignKey(
        AdminPermission,
        on_delete=models.CASCADE,
        related_name='admin_users'
    )

    class Meta:
        unique_together = ('admin_profile', 'permission')

    def __str__(self):
        return f"{self.admin_profile.user.email} -> {self.permission.codename}"


class Report(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        REVIEWING = 'REVIEWING', 'Reviewing'
        RESOLVED = 'RESOLVED', 'Resolved'
        REJECTED = 'REJECTED', 'Rejected'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='filed_reports'
    )
    reported_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reports_against'
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.CharField(max_length=255, null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    reason = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_reports'
    )

    def __str__(self):
        return f"Report {self.id} by {self.reporter.email} - {self.get_status_display()}"


class AdminActivityLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_activity_logs'
    )
    action = models.CharField(max_length=100)
    target = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.created_at.strftime('%Y-%m-%d %H:%M')} - {self.admin} - {self.action}"


class PlatformSettings(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    site_name = models.CharField(max_length=100, default='Hive')
    logo = models.ImageField(upload_to='branding/logo/', null=True, blank=True)
    favicon = models.ImageField(upload_to='branding/favicon/', null=True, blank=True)
    admin_logo = models.ImageField(upload_to='branding/admin/', null=True, blank=True)
    maintenance_mode = models.BooleanField(default=False)
    contact_email = models.EmailField(default='support@hive.com')
    registration_enabled = models.BooleanField(default=True)
    allow_google_login = models.BooleanField(default=True)
    default_profile_visibility = models.CharField(max_length=20, default='PUBLIC')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_platform_settings'
    )

    def save(self, *args, **kwargs):
        # Singleton pattern enforcement
        self.pk = self.pk or uuid.UUID('00000000-0000-0000-0000-000000000001')
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=uuid.UUID('00000000-0000-0000-0000-000000000001'))
        return obj

    @property
    def logo_url(self):
        if self.logo:
            return self.logo.url
        return '/static/images/branding/hive_logo.svg'

    @property
    def favicon_url(self):
        if self.favicon:
            return self.favicon.url
        return '/static/favicon.svg'

    @property
    def admin_logo_url(self):
        if self.admin_logo:
            return self.admin_logo.url
        return self.logo_url

    @property
    def updated_at_timestamp(self):
        if self.updated_at:
            return int(self.updated_at.timestamp())
        return 1

    def __str__(self):
        return f"Platform Settings ({self.site_name})"

