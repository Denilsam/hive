from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Q
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from apps.chat.models import Conversation, Message
from apps.connections.models import Follow
from apps.api.serializers import (
    ConversationSerializer,
    MessageSerializer,
    StartConversationSerializer,
)

User = get_user_model()


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50


class ConversationListCreateView(APIView):
    """
    GET /api/v1/chat/conversations/ (Paginated list of conversations for authenticated user)
    POST /api/v1/chat/conversations/start/ or POST /api/v1/chat/conversations/ (Start conversation)
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request, *args, **kwargs):
        conversations = Conversation.objects.filter(
            Q(user1=request.user) | Q(user2=request.user)
        ).filter(
            user1__is_superuser=False,
            user2__is_superuser=False
        ).select_related('user1', 'user1__profile', 'user2', 'user2__profile').order_by('-updated_at')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(conversations, request)

        if page is not None:
            serializer = ConversationSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = ConversationSerializer(conversations, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = StartConversationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        target_user_id = serializer.validated_data['user_id']
        if request.user.id == target_user_id:
            return Response({"detail": "You cannot start a conversation with yourself."}, status=status.HTTP_400_BAD_REQUEST)

        other_user = get_object_or_404(User, id=target_user_id)
        if other_user.is_superuser or request.user.is_superuser:
            return Response({"detail": "Messaging is not available for administrative accounts."}, status=status.HTTP_400_BAD_REQUEST)

        conversation, created = Conversation.get_or_create_conversation(request.user, other_user)
        res_serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(res_serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ConversationDetailView(APIView):
    """
    GET /api/v1/chat/conversations/<id>/
    Retrieve detail for a specific conversation.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        conversation = get_object_or_404(Conversation, id=id)

        if request.user != conversation.user1 and request.user != conversation.user2:
            return Response({"detail": "You do not have permission to access this conversation."}, status=status.HTTP_403_FORBIDDEN)

        if conversation.user1.is_superuser or conversation.user2.is_superuser:
            return Response({"detail": "Messaging is not available for this conversation."}, status=status.HTTP_403_FORBIDDEN)

        serializer = ConversationSerializer(conversation, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class MessageListCreateView(APIView):
    """
    GET /api/v1/chat/conversations/<id>/messages/ (Paginated message history)
    POST /api/v1/chat/conversations/<id>/messages/ (Send message via REST)
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request, id, *args, **kwargs):
        conversation = get_object_or_404(Conversation, id=id)

        if request.user != conversation.user1 and request.user != conversation.user2:
            return Response({"detail": "You do not have permission to access this conversation."}, status=status.HTTP_403_FORBIDDEN)

        # Mark unread messages sent by the other user as read
        conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

        messages = conversation.messages.select_related('sender', 'sender__profile').order_by('created_at')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(messages, request)

        if page is not None:
            serializer = MessageSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = MessageSerializer(messages, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, id, *args, **kwargs):
        conversation = get_object_or_404(Conversation, id=id)

        if request.user != conversation.user1 and request.user != conversation.user2:
            return Response({"detail": "You do not have permission to access this conversation."}, status=status.HTTP_403_FORBIDDEN)

        if conversation.user1.is_superuser or conversation.user2.is_superuser:
            return Response({"detail": "Messaging is not available for this conversation."}, status=status.HTTP_403_FORBIDDEN)

        content = request.data.get('content') or request.data.get('message', '')
        content = str(content).strip()

        if not content:
            return Response({"content": ["Message content cannot be empty."]}, status=status.HTTP_400_BAD_REQUEST)

        # Check mutual follow rule
        other_user = conversation.get_other_user(request.user)
        if other_user:
            user_follows = Follow.objects.filter(follower=request.user, following=other_user).exists()
            other_follows = Follow.objects.filter(follower=other_user, following=request.user).exists()
            if not (user_follows and other_follows):
                return Response({"detail": "You can only message users with whom you share a mutual connection/follow."}, status=status.HTTP_400_BAD_REQUEST)

        msg = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content
        )

        # Broadcast via Channel layer if active
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f'chat_{conversation.id}',
                {
                    'type': 'chat_message',
                    'message': msg.content,
                    'sender_email': request.user.email,
                    'sender_name': f"{request.user.first_name} {request.user.last_name}",
                    'created_at': msg.created_at.isoformat(),
                    'is_read': msg.is_read
                }
            )

        serializer = MessageSerializer(msg, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
