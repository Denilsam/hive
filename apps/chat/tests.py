from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Q

from .models import Conversation, Message

User = get_user_model()


class ChatSystemTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create users
        self.user1 = User.objects.create_user(
            email='alice@example.com',
            password='StrongPassword123!',
            first_name='Alice',
            last_name='Smith',
            is_active=True
        )
        self.user2 = User.objects.create_user(
            email='bob@example.com',
            password='StrongPassword123!',
            first_name='Bob',
            last_name='Jones',
            is_active=True
        )
        self.user3 = User.objects.create_user(
            email='charlie@example.com',
            password='StrongPassword123!',
            first_name='Charlie',
            last_name='Brown',
            is_active=True
        )

        # Ensure user1.id < user2.id for ordering assertions
        if self.user1.id > self.user2.id:
            self.user1, self.user2 = self.user2, self.user1

        self.conv = Conversation.objects.create(user1=self.user1, user2=self.user2)

    def test_start_conversation_view_without_mutual_follow_requirement(self):
        start_url_charlie = reverse('chat:start_conversation', kwargs={'user_id': self.user3.id})

        # 1. Alice messages Charlie directly without mutual follow
        self.client.login(email='alice@example.com', password='StrongPassword123!')
        response = self.client.get(start_url_charlie)
        self.assertEqual(response.status_code, 302)

        conv = Conversation.objects.filter(
            (Q(user1=self.user1, user2=self.user3) | Q(user1=self.user3, user2=self.user1))
        ).first()
        self.assertIsNotNone(conv)
        self.assertRedirects(response, reverse('chat:chat_room', kwargs={'conversation_id': conv.id}))

        # 2. Charlie messages Alice -> returns the exact SAME conversation (no duplicate)
        self.client.login(email='charlie@example.com', password='StrongPassword123!')
        start_url_alice = reverse('chat:start_conversation', kwargs={'user_id': self.user1.id})
        response2 = self.client.get(start_url_alice)
        self.assertEqual(response2.status_code, 302)
        self.assertRedirects(response2, reverse('chat:chat_room', kwargs={'conversation_id': conv.id}))

    def test_conversation_creation_and_ordering(self):
        # 1. Check self-chat prevention
        self_chat = Conversation(user1=self.user1, user2=self.user1)
        with self.assertRaises(ValidationError):
            self_chat.full_clean()

        # 2. Check automatic ordering (user1.id < user2.id)
        # Attempt to create conversation with user2 and user3 in reverse order of IDs
        u_first, u_second = (self.user2, self.user3) if self.user2.id < self.user3.id else (self.user3, self.user2)
        conv_reverse = Conversation(user1=u_second, user2=u_first)
        conv_reverse.full_clean()
        self.assertEqual(conv_reverse.user1, u_first)
        self.assertEqual(conv_reverse.user2, u_second)

    def test_duplicate_conversation_prevention(self):
        # Already created user1 and user2 pair in setUp
        # Attempting to save another pair should trigger IntegrityError due to unique constraint
        dup = Conversation(user1=self.user1, user2=self.user2)
        with self.assertRaises(ValidationError):
            dup.full_clean()
            dup.save()

    def test_message_creation_and_member_validation(self):
        # 1. Member Alice sends message (valid)
        msg1 = Message.objects.create(conversation=self.conv, sender=self.user1, content="Hello Bob")
        self.assertEqual(msg1.content, "Hello Bob")
        
        # 2. Non-member Charlie tries to send message in Alice/Bob chat (ValidationError)
        msg_invalid = Message(conversation=self.conv, sender=self.user3, content="Spam")
        with self.assertRaises(ValidationError):
            msg_invalid.full_clean()

    def test_chat_room_view_permissions(self):
        room_url = reverse('chat:chat_room', kwargs={'conversation_id': self.conv.id})

        # 1. Non-member Charlie tries to access room (403 Forbidden)
        self.client.login(email='charlie@example.com', password='StrongPassword123!')
        response = self.client.get(room_url)
        self.assertEqual(response.status_code, 403)

        # 2. Member Bob accesses room successfully
        self.client.login(email='bob@example.com', password='StrongPassword123!')
        response = self.client.get(room_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alice Smith")

    def test_send_message_view_http_and_ajax(self):
        send_url = reverse('chat:send_message', kwargs={'conversation_id': self.conv.id})

        # 1. Alice sends message via AJAX POST
        self.client.login(email='alice@example.com', password='StrongPassword123!')
        response = self.client.post(send_url, {'content': 'Hello Bob from browser!'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        
        # Verify saved in DB
        self.assertEqual(Message.objects.filter(conversation=self.conv).count(), 1)
        msg_db = Message.objects.filter(conversation=self.conv).first()
        self.assertEqual(msg_db.sender, self.user1)
        self.assertEqual(msg_db.content, 'Hello Bob from browser!')

        # 2. Bob logs in and checks chat room -> sees Alice's message
        self.client.login(email='bob@example.com', password='StrongPassword123!')
        room_url = reverse('chat:chat_room', kwargs={'conversation_id': self.conv.id})
        response_bob = self.client.get(room_url)
        self.assertEqual(response_bob.status_code, 200)
        self.assertContains(response_bob, 'Hello Bob from browser!')

        # 3. Bob replies to Alice via AJAX POST
        response_reply = self.client.post(send_url, {'content': 'Hi Alice! Received loud and clear.'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response_reply.status_code, 200)
        self.assertEqual(Message.objects.filter(conversation=self.conv).count(), 2)

        # 4. Alice logs in and checks chat room -> sees both messages in order
        self.client.login(email='alice@example.com', password='StrongPassword123!')
        response_alice = self.client.get(room_url)
        self.assertEqual(response_alice.status_code, 200)
        self.assertContains(response_alice, 'Hello Bob from browser!')
        self.assertContains(response_alice, 'Hi Alice! Received loud and clear.')

        # 5. Non-member Charlie tries to send a message -> 403 Forbidden
        self.client.login(email='charlie@example.com', password='StrongPassword123!')
        res_charlie = self.client.post(send_url, {'content': 'Hacking into chat'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(res_charlie.status_code, 403)

    def test_superuser_messaging_exclusion_and_security(self):
        # Create a superadmin user (with or without an accidental Profile)
        superuser = User.objects.create_superuser(
            email='superadmin_chat@connect.com',
            password='Password123!',
            first_name='Super',
            last_name='Admin'
        )
        from apps.profiles.models import Profile
        Profile.objects.get_or_create(user=superuser)

        # 1. StartConversationView blocked for superuser target
        start_url_su = reverse('chat:start_conversation', kwargs={'user_id': superuser.id})
        self.client.login(email='alice@example.com', password='StrongPassword123!')
        res_start = self.client.get(start_url_su)
        self.assertEqual(res_start.status_code, 302)
        self.assertRedirects(res_start, reverse('chat:inbox'), fetch_redirect_response=False)

        # 2. Existing Conversation involving superuser excluded from InboxView
        conv_su = Conversation.objects.create(user1=self.user1, user2=superuser)
        inbox_url = reverse('chat:inbox')
        res_inbox = self.client.get(inbox_url)
        # InboxView returns 200 OK and excludes superuser conversation from list
        self.assertEqual(res_inbox.status_code, 200)
        self.assertContains(res_inbox, "Bob Jones")
        self.assertNotContains(res_inbox, "Super Admin")

        # 3. ChatRoomView for superuser conversation returns 403 Forbidden
        room_su_url = reverse('chat:chat_room', kwargs={'conversation_id': conv_su.id})
        res_room = self.client.get(room_su_url)
        self.assertEqual(res_room.status_code, 403)

        # 4. SendMessageView into superuser conversation returns 403 Forbidden
        send_su_url = reverse('chat:send_message', kwargs={'conversation_id': conv_su.id})
        res_send = self.client.post(send_su_url, {'content': 'Hello Admin'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(res_send.status_code, 403)

    def test_inbox_view_renders_conversation_list_and_mobile_navigation(self):
        # 1. Login user1 and request Inbox URL directly -> 200 OK
        self.client.login(email='alice@example.com', password='StrongPassword123!')
        inbox_url = reverse('chat:inbox')
        response = self.client.get(inbox_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'chat/inbox.html')
        self.assertContains(response, "Bob Jones")

        # 2. Open chat room -> verify back button links to canonical Inbox URL
        chat_room_url = reverse('chat:chat_room', kwargs={'conversation_id': self.conv.id})
        response_room = self.client.get(chat_room_url)
        self.assertEqual(response_room.status_code, 200)
        self.assertTemplateUsed(response_room, 'chat/chat_room.html')
        self.assertContains(response_room, inbox_url)


from channels.testing import WebsocketCommunicator
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from datetime import timedelta
from apps.connections.models import Follow
from config.asgi import application


class Phase2CChatTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user1 = User.objects.create_user(
            email='alice.chat@example.com',
            password='Password123!',
            first_name='Alice',
            last_name='Chat',
            is_active=True
        )
        self.user2 = User.objects.create_user(
            email='bob.chat@example.com',
            password='Password123!',
            first_name='Bob',
            last_name='Chat',
            is_active=True
        )
        self.user3 = User.objects.create_user(
            email='eve.chat@example.com',
            password='Password123!',
            first_name='Eve',
            last_name='Hacker',
            is_active=True
        )

        # Establish mutual follow between User1 and User2
        Follow.objects.create(follower=self.user1, following=self.user2)
        Follow.objects.create(follower=self.user2, following=self.user1)

        self.conv, _ = Conversation.get_or_create_conversation(self.user1, self.user2)

        self.refresh1 = RefreshToken.for_user(self.user1)
        self.access1 = str(self.refresh1.access_token)

        self.refresh3 = RefreshToken.for_user(self.user3)
        self.access3 = str(self.refresh3.access_token)

    def auth_client(self, token):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return client

    def test_rest_chat_conversations_list_and_start(self):
        client = self.auth_client(self.access1)
        list_url = reverse('api:chat_conversations_list')
        res1 = client.get(list_url)
        self.assertEqual(res1.status_code, 200)
        self.assertEqual(len(res1.data['results']), 1)

        # Start conversation with User3
        start_url = reverse('api:chat_conversations_start')
        res2 = client.post(start_url, {'user_id': self.user3.id}, format='json')
        self.assertEqual(res2.status_code, 201)
        self.assertIn('id', res2.data)

    def test_rest_chat_messages_history_and_send(self):
        client = self.auth_client(self.access1)
        msg_url = reverse('api:chat_messages_list_create', kwargs={'id': self.conv.id})

        # Send message via REST
        res_send = client.post(msg_url, {'content': 'Hello Bob from REST'}, format='json')
        self.assertEqual(res_send.status_code, 201)
        self.assertEqual(res_send.data['content'], 'Hello Bob from REST')

        # Read message history via REST
        res_hist = client.get(msg_url)
        self.assertEqual(res_hist.status_code, 200)
        self.assertEqual(len(res_hist.data['results']), 1)

    def test_rest_unauthorized_conversation_access(self):
        client3 = self.auth_client(self.access3)
        msg_url = reverse('api:chat_messages_list_create', kwargs={'id': self.conv.id})

        # Eve tries to read Alice/Bob messages -> 403
        res_read = client3.get(msg_url)
        self.assertEqual(res_read.status_code, 403)

        # Eve tries to send message in Alice/Bob chat -> 403
        res_send = client3.post(msg_url, {'content': 'Hacking message'}, format='json')
        self.assertEqual(res_send.status_code, 403)

    async def test_websocket_jwt_connection_success(self):
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.conv.id}/?token={self.access1}")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.disconnect()

    async def test_websocket_invalid_token_rejection(self):
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.conv.id}/?token=invalid_token_string")
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_websocket_expired_token_rejection(self):
        expired = AccessToken.for_user(self.user1)
        expired.set_exp(lifetime=-timedelta(days=1))
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.conv.id}/?token={str(expired)}")
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_websocket_non_member_rejection(self):
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.conv.id}/?token={self.access3}")
        connected, _ = await communicator.connect()
        self.assertFalse(connected)

    async def test_websocket_send_and_receive_broadcast(self):
        communicator1 = WebsocketCommunicator(application, f"/ws/chat/{self.conv.id}/?token={self.access1}")
        connected1, _ = await communicator1.connect()
        self.assertTrue(connected1)

        # Send message via WebSocket
        await communicator1.send_json_to({"message": "Hello from WebSocket!"})

        # Receive broadcast
        response = await communicator1.receive_json_from()
        self.assertEqual(response['message'], 'Hello from WebSocket!')
        self.assertEqual(response['sender_email'], 'alice.chat@example.com')

        await communicator1.disconnect()

    async def test_websocket_malformed_payload_handling(self):
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.conv.id}/?token={self.access1}")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Send malformed string instead of JSON
        await communicator.send_to("Not a valid JSON string")
        # Ensure connection stays alive without crashing
        await communicator.send_json_to({"message": "Valid after malformed"})
        response = await communicator.receive_json_from()
        self.assertEqual(response['message'], 'Valid after malformed')

        await communicator.disconnect()


