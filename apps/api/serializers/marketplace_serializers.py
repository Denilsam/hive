from rest_framework import serializers
from apps.marketplace.models import Collaboration, CollaborationSkill, CollaborationApplication
from apps.profiles.models import Skill
from .auth_serializers import UserSerializer
from .profile_serializers import SkillSerializer


class CollaborationSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source='skill.name', read_only=True)

    class Meta:
        model = CollaborationSkill
        fields = ['id', 'skill', 'skill_name']


class CollaborationApplicationSerializer(serializers.ModelSerializer):
    applicant = UserSerializer(read_only=True)
    collaboration_title = serializers.CharField(source='collaboration.title', read_only=True)

    class Meta:
        model = CollaborationApplication
        fields = [
            'id',
            'collaboration',
            'collaboration_title',
            'applicant',
            'message',
            'status',
            'created_at',
        ]
        read_only_fields = ['id', 'collaboration', 'applicant', 'status', 'created_at']


class CollaborationSerializer(serializers.ModelSerializer):
    creator = UserSerializer(read_only=True)
    required_skills = CollaborationSkillSerializer(many=True, read_only=True)
    skill_ids = serializers.PrimaryKeyRelatedField(
        queryset=Skill.objects.all(),
        many=True,
        write_only=True,
        required=False
    )
    application_count = serializers.SerializerMethodField()
    has_applied = serializers.SerializerMethodField()

    class Meta:
        model = Collaboration
        fields = [
            'id',
            'creator',
            'title',
            'description',
            'category',
            'project_type',
            'budget_type',
            'budget_amount',
            'duration',
            'status',
            'required_skills',
            'skill_ids',
            'application_count',
            'has_applied',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'creator', 'created_at', 'updated_at']

    def get_application_count(self, obj):
        return obj.applications.count()

    def get_has_applied(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if not user or user.is_anonymous:
            return False
        return CollaborationApplication.objects.filter(collaboration=obj, applicant=user).exists()

    def create(self, validated_data):
        skill_ids = validated_data.pop('skill_ids', [])
        collaboration = Collaboration.objects.create(**validated_data)
        for skill in skill_ids:
            CollaborationSkill.objects.create(collaboration=collaboration, skill=skill)
        return collaboration
