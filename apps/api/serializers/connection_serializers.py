from rest_framework import serializers
from apps.connections.models import Follow, ConnectionRequest, Connection
from .auth_serializers import UserSerializer


class FollowSerializer(serializers.ModelSerializer):
    follower = UserSerializer(read_only=True)
    following = UserSerializer(read_only=True)

    class Meta:
        model = Follow
        fields = ['id', 'follower', 'following', 'created_at']
        read_only_fields = ['id', 'follower', 'following', 'created_at']


class ConnectionRequestSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    receiver = UserSerializer(read_only=True)

    class Meta:
        model = ConnectionRequest
        fields = ['id', 'sender', 'receiver', 'status', 'created_at', 'updated_at']
        read_only_fields = ['id', 'sender', 'receiver', 'status', 'created_at', 'updated_at']


class ConnectionSerializer(serializers.ModelSerializer):
    user1 = UserSerializer(read_only=True)
    user2 = UserSerializer(read_only=True)

    class Meta:
        model = Connection
        fields = ['id', 'user1', 'user2', 'created_at']
        read_only_fields = ['id', 'user1', 'user2', 'created_at']
