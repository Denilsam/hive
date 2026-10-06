from rest_framework import serializers
from apps.notifications.models import Notification
from .auth_serializers import UserSerializer


class NotificationSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = [
            'id',
            'receiver',
            'sender',
            'notification_type',
            'message',
            'related_url',
            'is_read',
            'created_at',
        ]
        read_only_fields = fields
