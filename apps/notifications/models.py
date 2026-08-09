from django.db import models
from django.conf import settings


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        LIKE = 'LIKE', 'Like'
        COMMENT = 'COMMENT', 'Comment'
        FOLLOW = 'FOLLOW', 'Follow'
        CONNECTION_REQUEST = 'CONNECTION_REQUEST', 'Connection Request'
        CONNECTION_ACCEPTED = 'CONNECTION_ACCEPTED', 'Connection Accepted'
        MESSAGE = 'MESSAGE', 'New Message'
        PORTFOLIO_VIEW = 'PORTFOLIO_VIEW', 'Portfolio View'
        COMMUNITY_ACTIVITY = 'COMMUNITY_ACTIVITY', 'Community Activity'

    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_notifications',
        null=True,
        blank=True
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices
    )
    message = models.CharField(max_length=255)
    related_url = models.CharField(max_length=255, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} Notification for {self.receiver.email}"
