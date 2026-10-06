from rest_framework import serializers
from apps.chat.models import Conversation, Message
from .auth_serializers import UserSerializer


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'content', 'is_read', 'created_at']
        read_only_fields = ['id', 'conversation', 'sender', 'is_read', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    user1 = UserSerializer(read_only=True)
    user2 = UserSerializer(read_only=True)
    other_user = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            'id',
            'user1',
            'user2',
            'other_user',
            'last_message',
            'unread_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = fields

    def get_other_user(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if not user or user.is_anonymous:
            return None
        other = obj.get_other_user(user)
        if other:
            return UserSerializer(other, context=self.context).data
        return None

    def get_last_message(self, obj):
        last_msg = obj.messages.order_by('-created_at').first()
        if last_msg:
            return MessageSerializer(last_msg, context=self.context).data
        return None

    def get_unread_count(self, obj):
        request = self.context.get('request')
        user = request.user if request else None
        if not user or user.is_anonymous:
            return 0
        return obj.messages.filter(is_read=False).exclude(sender=user).count()


class StartConversationSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=True)
