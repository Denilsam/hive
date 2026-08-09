from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
import json

class SendMessageView(LoginRequiredMixin, View):
    def post(self, request, conversation_id):
        conversation = get_object_or_404(Conversation, id=conversation_id)

        # Security check: request.user must belong to conversation AND neither participant is a superuser
        if (request.user != conversation.user1 and request.user != conversation.user2) or conversation.user1.is_superuser or conversation.user2.is_superuser:
            is_ajax = (
                request.headers.get('x-requested-with') == 'XMLHttpRequest'
                or 'application/json' in request.headers.get('accept', '')
                or request.content_type == 'application/json'
            )
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Permission denied.'}, status=403)
            return HttpResponseForbidden("Messaging is not available for this conversation.")

        # Read content from POST form data or JSON body
        if request.content_type == 'application/json':
            try:
                data = json.loads(request.body)
                content = data.get('content') or data.get('message', '')
            except Exception:
                content = ''
        else:
            content = request.POST.get('content') or request.POST.get('message', '')

        content = str(content).strip()
        if not content:
            is_ajax = (
                request.headers.get('x-requested-with') == 'XMLHttpRequest'
                or 'application/json' in request.headers.get('accept', '')
                or request.content_type == 'application/json'
            )
            if is_ajax:
                return JsonResponse({'success': False, 'error': 'Message content cannot be empty.'}, status=400)
            messages.error(request, "Message content cannot be empty.")
            return redirect('chat:chat_room', conversation_id=conversation.id)

        msg = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=content
        )

        is_ajax = (
            request.headers.get('x-requested-with') == 'XMLHttpRequest'
            or 'application/json' in request.headers.get('accept', '')
            or request.content_type == 'application/json'
        )

        if is_ajax:
            return JsonResponse({
                'success': True,
                'message': {
                    'id': msg.id,
                    'content': msg.content,
                    'sender_id': msg.sender.id,
                    'sender_name': f"{msg.sender.first_name} {msg.sender.last_name}",
                    'sender_email': msg.sender.email,
                    'created_at': msg.created_at.strftime('%I:%M %p')
                }
            })

        return redirect('chat:chat_room', conversation_id=conversation.id)

from .models import Conversation, Message

User = get_user_model()


class InboxView(LoginRequiredMixin, View):
    template_name = 'chat/inbox.html'

    def get(self, request):
        # Fetch conversations excluding superusers
        conversations = Conversation.objects.filter(
            Q(user1=request.user) | Q(user2=request.user)
        ).filter(
            user1__is_superuser=False,
            user2__is_superuser=False
        ).select_related('user1', 'user1__profile', 'user2', 'user2__profile').order_by('-updated_at')

        # Prepare conversations data (e.g. status of other user, last message)
        conversation_list = []
        for conv in conversations:
            other_user = conv.get_other_user(request.user)
            last_message = conv.messages.all().last()
            conversation_list.append({
                'conversation': conv,
                'other_user': other_user,
                'last_message': last_message
            })

        return render(request, self.template_name, {
            'conversations': conversation_list,
            'active_conversation': None,
            'messages': []
        })


class ChatRoomView(LoginRequiredMixin, View):
    template_name = 'chat/chat_room.html'

    def get(self, request, conversation_id):
        # Fetch selected conversation
        conversation = get_object_or_404(Conversation, id=conversation_id)

        # Security check: user must belong to conversation and neither participant is superuser
        if (request.user != conversation.user1 and request.user != conversation.user2) or conversation.user1.is_superuser or conversation.user2.is_superuser:
            return HttpResponseForbidden("You do not have permission to view this conversation.")

        # Fetch all eligible conversations for the sidebar (excluding superusers)
        conversations = Conversation.objects.filter(
            Q(user1=request.user) | Q(user2=request.user)
        ).filter(
            user1__is_superuser=False,
            user2__is_superuser=False
        ).select_related('user1', 'user1__profile', 'user2', 'user2__profile').order_by('-updated_at')

        conversation_list = []
        for conv in conversations:
            other_user = conv.get_other_user(request.user)
            last_message = conv.messages.all().last()
            conversation_list.append({
                'conversation': conv,
                'other_user': other_user,
                'last_message': last_message
            })

        # Mark all messages in this conversation not sent by request.user as read
        conversation.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

        # Fetch messages for this room
        msgs = conversation.messages.select_related('sender', 'sender__profile').all()
        other_user = conversation.get_other_user(request.user)

        return render(request, self.template_name, {
            'conversations': conversation_list,
            'active_conversation': conversation,
            'other_user': other_user,
            'messages_list': msgs
        })


class StartConversationView(LoginRequiredMixin, View):
    def get(self, request, user_id):
        other_user = get_object_or_404(User, id=user_id)
        if request.user == other_user:
            messages.error(request, "You cannot chat with yourself.")
            return redirect('chat:inbox')

        if other_user.is_superuser or request.user.is_superuser:
            messages.error(request, "Messaging is not available for administrative accounts.")
            return redirect('chat:inbox')

        conversation, created = Conversation.get_or_create_conversation(request.user, other_user)
        return redirect('chat:chat_room', conversation_id=conversation.id)
