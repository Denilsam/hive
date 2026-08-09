from django.urls import path
from .views import (
    FeedView, PostCreateView, PostDetailView,
    PostLikeToggleView, PostSaveToggleView,
    CommentCreateView, CommentDeleteView, PostDeleteView
)

app_name = 'posts'

urlpatterns = [
    path('feed/', FeedView.as_view(), name='feed'),
    path('posts/create/', PostCreateView.as_view(), name='create'),
    path('posts/<int:pk>/', PostDetailView.as_view(), name='post_detail'),
    path('posts/<int:pk>/delete/', PostDeleteView.as_view(), name='delete'),
    
    # AJAX Toggle / Operations
    path('posts/<int:pk>/like/', PostLikeToggleView.as_view(), name='like_toggle'),
    path('posts/<int:pk>/save/', PostSaveToggleView.as_view(), name='save_toggle'),
    path('posts/<int:pk>/comment/', CommentCreateView.as_view(), name='comment_create'),
    path('comments/<int:pk>/delete/', CommentDeleteView.as_view(), name='comment_delete'),
]
