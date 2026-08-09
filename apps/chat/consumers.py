import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Conversation, Message

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        
        # Deny connection if user is not authenticated
        if not self.user.is_authenticated:
            await self.close()
            return
            
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.room_group_name = f'chat_{self.conversation_id}'
        
        # Verify user belongs to conversation
        is_member = await self.is_conversation_member(self.user, self.conversation_id)
        if not is_member:
            await self.close()
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    # Receive message from WebSocket
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return
            
        content = data.get('message', '').strip()
        if not content:
            return

        # Verify mutual follow between users before proceeding
        is_mutual = await self.are_users_mutual_followers(self.user, self.conversation_id)
        if not is_mutual:
            return

        # Save message to database
        msg = await self.save_message(self.user, self.conversation_id, content)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': content,
                'sender_email': self.user.email,
                'sender_name': f"{self.user.first_name} {self.user.last_name}",
                'created_at': msg.created_at.isoformat(),
                'is_read': msg.is_read
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender_email': event['sender_email'],
            'sender_name': event['sender_name'],
            'created_at': event['created_at'],
            'is_read': event['is_read']
        }))

    @database_sync_to_async
    def is_conversation_member(self, user, conversation_id):
        try:
            conv = Conversation.objects.get(id=conversation_id)
            return user == conv.user1 or user == conv.user2
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def are_users_mutual_followers(self, user, conversation_id):
        from apps.connections.models import Follow
        try:
            conv = Conversation.objects.get(id=conversation_id)
            other_user = conv.get_other_user(user)
            if not other_user:
                return False
            user_follows_other = Follow.objects.filter(follower=user, following=other_user).exists()
            other_follows_user = Follow.objects.filter(follower=other_user, following=user).exists()
            return user_follows_other and other_follows_user
        except Conversation.DoesNotExist:
            return False

    @database_sync_to_async
    def save_message(self, user, conversation_id, content):
        conv = Conversation.objects.get(id=conversation_id)
        return Message.objects.create(
            conversation=conv,
            sender=user,
            content=content
        )
