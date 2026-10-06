from rest_framework import serializers
from apps.portfolio.models import Project, ProjectImage, ProjectLike, ProjectComment
from apps.profiles.models import Skill
from .auth_serializers import UserSerializer
from .profile_serializers import SkillSerializer


class ProjectImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProjectImage
        fields = ['id', 'image', 'image_url', 'caption', 'created_at']
        extra_kwargs = {'image': {'write_only': True}}

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image:
            url = obj.image.url
            if request and not url.startswith(('http://', 'https://')):
                return request.build_absolute_uri(url)
            return url
        return None


class ProjectCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ProjectComment
        fields = ['id', 'project', 'user', 'content', 'created_at']
        read_only_fields = ['id', 'project', 'user', 'created_at']


class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    project_image_url = serializers.SerializerMethodField()
    youtube_embed_url = serializers.CharField(read_only=True)
    technologies = SkillSerializer(many=True, read_only=True)
    technology_ids = serializers.PrimaryKeyRelatedField(
        queryset=Skill.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source='technologies'
    )
    gallery_images = ProjectImageSerializer(source='images', many=True, read_only=True)
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            'id',
            'owner',
            'title',
            'slug',
            'short_description',
            'description',
            'category',
            'project_image',
            'project_image_url',
            'youtube_embed_url',
            'technologies',
            'technology_ids',
            'github_url',
            'demo_url',
            'video_url',
            'start_date',
            'end_date',
            'is_featured',
            'visibility',
            'gallery_images',
            'like_count',
            'is_liked',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'owner', 'slug', 'created_at', 'updated_at']
        extra_kwargs = {
            'project_image': {'write_only': True, 'required': False}
        }

    def get_project_image_url(self, obj):
        request = self.context.get('request')
        if obj.project_image:
            url = obj.project_image.url
            if request and not url.startswith(('http://', 'https://')):
                return request.build_absolute_uri(url)
            return url
        return None

    def get_like_count(self, obj):
        return obj.likes.count()

    def get_is_liked(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if not user or user.is_anonymous:
            return False
        return ProjectLike.objects.filter(project=obj, user=user).exists()
