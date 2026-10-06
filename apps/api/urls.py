from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('', views.api_root, name='root'),

    # Phase 2A Authentication Endpoints
    path('v1/auth/register/', views.MobileRegisterView.as_view(), name='auth_register'),
    path('v1/auth/token/', views.MobileTokenObtainPairView.as_view(), name='auth_token_obtain'),
    path('v1/auth/token/refresh/', views.TokenRefreshView.as_view(), name='auth_token_refresh'),
    path('v1/auth/me/', views.CurrentUserView.as_view(), name='auth_me'),
    path('v1/auth/otp/verify/', views.MobileOTPVerifyView.as_view(), name='auth_otp_verify'),

    # Profiles Endpoints
    path('v1/profiles/me/', views.MyProfileView.as_view(), name='profile_me'),
    path('v1/profiles/<int:user_id>/', views.UserProfileDetailView.as_view(), name='profile_detail'),

    # Posts & Feed Endpoints
    path('v1/posts/', views.PostListCreateView.as_view(), name='posts_list_create'),
    path('v1/posts/<int:post_id>/', views.PostDetailView.as_view(), name='post_detail'),
    path('v1/posts/<int:post_id>/like/', views.PostLikeView.as_view(), name='post_like'),
    path('v1/posts/<int:post_id>/save/', views.PostSaveView.as_view(), name='post_save'),
    path('v1/posts/<int:post_id>/comments/', views.PostCommentListCreateView.as_view(), name='post_comments'),

    # Portfolio Endpoints
    path('v1/portfolio/projects/', views.ProjectListCreateView.as_view(), name='portfolio_projects_list_create'),
    path('v1/portfolio/projects/<int:project_id>/', views.ProjectDetailView.as_view(), name='portfolio_project_detail'),

    # Connections Endpoints
    path('v1/connections/follow/<int:user_id>/', views.FollowToggleView.as_view(), name='connections_follow_toggle'),
    path('v1/connections/followers/<int:user_id>/', views.FollowersListView.as_view(), name='connections_followers'),
    path('v1/connections/following/<int:user_id>/', views.FollowingListView.as_view(), name='connections_following'),
    path('v1/connections/requests/', views.ConnectionRequestListCreateView.as_view(), name='connections_requests'),
    path('v1/connections/request/<int:user_id>/', views.ConnectionRequestListCreateView.as_view(), name='connections_send_request'),
    path('v1/connections/request/<int:id>/<str:action>/', views.ConnectionRequestActionView.as_view(), name='connections_request_action'),
    path('v1/connections/network/', views.NetworkSummaryView.as_view(), name='connections_network_summary'),

    # Opportunities Routes
    path('v1/opportunities/', views.CollaborationListCreateView.as_view(), name='opportunities_list_create'),
    path('v1/opportunities/<int:id>/', views.CollaborationDetailView.as_view(), name='opportunities_detail'),
    path('v1/opportunities/<int:id>/apply/', views.CollaborationApplyView.as_view(), name='opportunities_apply'),
    path('v1/opportunities/my-applications/', views.MyApplicationsListView.as_view(), name='opportunities_my_applications'),

    # Marketplace Endpoints
    path('v1/marketplace/collaborations/', views.CollaborationListCreateView.as_view(), name='marketplace_collaborations'),
    path('v1/marketplace/collaborations/<int:id>/', views.CollaborationDetailView.as_view(), name='marketplace_collaboration_detail'),
    path('v1/marketplace/collaborations/<int:id>/apply/', views.CollaborationApplyView.as_view(), name='marketplace_collaboration_apply'),
    path('v1/marketplace/my-applications/', views.MyApplicationsListView.as_view(), name='marketplace_my_applications'),

    # Notifications Endpoints
    path('v1/notifications/', views.NotificationListView.as_view(), name='notifications_list'),
    path('v1/notifications/<int:id>/read/', views.NotificationMarkReadView.as_view(), name='notification_mark_read'),
    path('v1/notifications/read-all/', views.NotificationReadAllView.as_view(), name='notifications_read_all'),

    # Mobile Chat Endpoints (Phase 2C)
    path('v1/chat/conversations/', views.ConversationListCreateView.as_view(), name='chat_conversations_list'),
    path('v1/chat/conversations/start/', views.ConversationListCreateView.as_view(), name='chat_conversations_start'),
    path('v1/chat/conversations/<int:id>/', views.ConversationDetailView.as_view(), name='chat_conversation_detail'),
    path('v1/chat/conversations/<int:id>/messages/', views.MessageListCreateView.as_view(), name='chat_messages_list_create'),
]
