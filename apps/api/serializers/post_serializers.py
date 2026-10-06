from rest_framework import serializers
from apps.posts.models import Post, Comment, Like, SavedPost
from .auth_serializers import UserSerializer


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'post', 'user', 'content', 'created_at']
        read_only_fields = ['id', 'post', 'user', 'created_at']


class PostSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    image_url = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            'id',
            'author',
            'content',
            'image',
            'image_url',
            'video',
            'video_url',
            'post_type',
            'visibility',
            'like_count',
            'comment_count',
            'is_liked',
            'is_saved',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'author', 'created_at', 'updated_at']
        extra_kwargs = {
            'image': {'write_only': True, 'required': False},
            'video': {'write_only': True, 'required': False},
        }

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            url = obj.image.url
            if request and not url.startswith(('http://', 'https://')):
                return request.build_absolute_uri(url)
            return url
        return None

    def get_video_url(self, obj):
        request = self.context.get('request')
        if obj.video:
            url = obj.video.url
            if request and not url.startswith(('http://', 'https://')):
                return request.build_absolute_uri(url)
            return url
        return None

    def get_like_count(self, obj):
        if hasattr(obj, 'likes_count_annotated'):
            return obj.likes_count_annotated
        return obj.likes.count()

    def get_comment_count(self, obj):
        if hasattr(obj, 'comments_count_annotated'):
            return obj.comments_count_annotated
        return obj.comments.count()

    def get_is_liked(self, obj):
        user = self.context.get('request_user') or (self.context.get('request').user if self.context.get('request') else None)
        if not user or user.is_anonymous:
            return False
        if hasattr(obj, '_prefetched_user_likes'):
            return user.id in obj._prefetched_user_likes
        return Like.objects.filter(post=obj, user=user).exists()

    def get_is_saved(self, obj):
        user = self.context.get('request_user') or (self.context.get('request').user if self.context.get('request') else None)
        if not user or user.is_anonymous:
            return False
        if hasattr(obj, '_prefetched_user_saves'):
            return user.id in obj._prefetched_user_saves
        return SavedPost.objects.filter(post=obj, user=user).exists()

    def validate(self, attrs):
        content = attrs.get('content')
        image = attrs.get('image')
        video = attrs.get('video')

        # When creating (instance is None), enforce at least text content or media
        if self.instance is None and not content and not image and not video:
            raise serializers.ValidationError("A post must contain either text content or media (image/video).")
        return attrs
