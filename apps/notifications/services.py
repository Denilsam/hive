from .models import Notification
from django.contrib.auth import get_user_model
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

User = get_user_model()


def create_notification(receiver, sender, notification_type, message, related_url=None):
    # Prevent creating notification if sender is receiver (e.g. self-liking a post)
    if receiver == sender:
        return None

    # Notification Deduplication Safeguard: check for existing unread notification from same sender & type
    if sender and notification_type:
        existing = Notification.objects.filter(
            receiver=receiver,
            sender=sender,
            notification_type=notification_type,
            is_read=False
        ).first()
        if existing:
            # Re-use existing unread notification and refresh timestamp/message
            existing.message = message
            if related_url:
                existing.related_url = related_url
            existing.save()
            return existing

    notification = Notification.objects.create(
        receiver=receiver,
        sender=sender,
        notification_type=notification_type,
        message=message,
        related_url=related_url
    )

    # Optional: Send real-time notification via Channels channel layer
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"user_notifications_{receiver.id}",
                {
                    "type": "notification_message",
                    "notification": {
                        "id": notification.id,
                        "message": notification.message,
                        "notification_type": notification.notification_type,
                        "related_url": notification.related_url,
                        "created_at": notification.created_at.isoformat(),
                        "sender_name": f"{sender.first_name} {sender.last_name}" if sender else "System"
                    }
                }
            )
    except Exception:
        pass # Fallback if channel layer is not running or properly configured

    return notification


def mark_notification_read(notification_id, user):
    try:
        notification = Notification.objects.get(id=notification_id, receiver=user)
        notification.is_read = True
        notification.save()
        return True
    except Notification.DoesNotExist:
        return False


def mark_all_read(user):
    Notification.objects.filter(receiver=user, is_read=False).update(is_read=True)
