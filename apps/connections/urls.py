from django.urls import path
from .views import (
    NetworkDiscoveryView, FollowToggleView, SendRequestView,
    AcceptRequestView, RejectRequestView, CancelRequestView,
    RemoveConnectionView, FollowersListView, FollowingListView,
    RequestsListView
)

app_name = 'connections'

urlpatterns = [
    path('network/', NetworkDiscoveryView.as_view(), name='network'),
    path('network/followers/', FollowersListView.as_view(), name='followers'),
    path('network/followers/<str:username>/', FollowersListView.as_view(), name='user_followers'),
    path('network/following/', FollowingListView.as_view(), name='following'),
    path('network/following/<str:username>/', FollowingListView.as_view(), name='user_following'),
    path('network/requests/', RequestsListView.as_view(), name='requests'),
    
    # AJAX Toggle / Operations
    path('network/follow/<int:user_id>/', FollowToggleView.as_view(), name='follow_toggle'),
    path('network/request/send/<int:user_id>/', SendRequestView.as_view(), name='send_request'),
    path('network/request/accept/<int:pk>/', AcceptRequestView.as_view(), name='accept_request'),
    path('network/request/reject/<int:pk>/', RejectRequestView.as_view(), name='reject_request'),
    path('network/request/cancel/<int:pk>/', CancelRequestView.as_view(), name='cancel_request'),
    path('network/connection/remove/<int:user_id>/', RemoveConnectionView.as_view(), name='remove_connection'),
]
