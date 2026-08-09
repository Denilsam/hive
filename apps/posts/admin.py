from django.contrib import admin
from .models import Post, Comment, Like, SavedPost


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """
    Expose user posts with lists, category filters, and calculated engagement metrics.
    """
    list_display = ('id', 'author', 'post_type', 'get_likes_count', 'get_comments_count', 'created_at')
    list_filter = ('post_type', 'created_at')
    search_fields = ('author__email', 'content', 'post_type')

    def get_likes_count(self, obj):
        return obj.likes.count()
    get_likes_count.short_description = 'Likes Count'

    def get_comments_count(self, obj):
        return obj.comments.count()
    get_comments_count.short_description = 'Comments Count'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'post', 'created_at')
    search_fields = ('user__email', 'content')


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')
    search_fields = ('user__email', 'post__id')


@admin.register(SavedPost)
class SavedPostAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'created_at')
    search_fields = ('user__email', 'post__id')
