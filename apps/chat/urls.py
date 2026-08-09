from django.urls import path
from .views import InboxView, ChatRoomView, StartConversationView, SendMessageView

app_name = 'chat'

urlpatterns = [
    path('inbox/', InboxView.as_view(), name='inbox'),
    path('chat/<int:conversation_id>/', ChatRoomView.as_view(), name='chat_room'),
    path('chat/<int:conversation_id>/send/', SendMessageView.as_view(), name='send_message'),
    path('chat/start/<int:user_id>/', StartConversationView.as_view(), name='start_conversation'),
]
