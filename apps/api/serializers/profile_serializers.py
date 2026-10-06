from rest_framework import serializers
from apps.profiles.models import Profile, Education, Experience, UserSkill, Skill, Certificate
from .auth_serializers import UserSerializer


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name']


class UserSkillSerializer(serializers.ModelSerializer):
    skill_name = serializers.CharField(source='skill.name', read_only=True)

    class Meta:
        model = UserSkill
        fields = ['id', 'skill', 'skill_name', 'level']


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = ['id', 'degree', 'institution', 'field_of_study', 'start_year', 'end_year', 'description']


class ExperienceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experience
        fields = ['id', 'company_name', 'role', 'employment_type', 'start_date', 'end_date', 'currently_working', 'description']


class CertificateSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = ['id', 'title', 'organization', 'issue_date', 'certificate_url', 'file_url']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.certificate_file:
            url = obj.certificate_file.url
            if request and not url.startswith(('http://', 'https://')):
                return request.build_absolute_uri(url)
            return url
        return None


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    profile_image_url = serializers.SerializerMethodField()
    cover_image_url = serializers.SerializerMethodField()
    education = EducationSerializer(source='user.education_set', many=True, read_only=True)
    experience = ExperienceSerializer(source='user.experience_set', many=True, read_only=True)
    skills = UserSkillSerializer(source='user.userskill_set', many=True, read_only=True)
    certificates = CertificateSerializer(source='user.certificate_set', many=True, read_only=True)
    completion_percentage = serializers.IntegerField(read_only=True)

    class Meta:
        model = Profile
        fields = [
            'id',
            'user',
            'profile_image',
            'profile_image_url',
            'cover_image',
            'cover_image_url',
            'headline',
            'bio',
            'location',
            'website',
            'github_url',
            'linkedin_url',
            'twitter_url',
            'phone_number',
            'completion_percentage',
            'education',
            'experience',
            'skills',
            'certificates',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'user', 'completion_percentage', 'created_at', 'updated_at']
        extra_kwargs = {
            'profile_image': {'write_only': True, 'required': False},
            'cover_image': {'write_only': True, 'required': False},
        }

    def get_profile_image_url(self, obj):
        request = self.context.get('request')
        if obj.profile_image:
            url = obj.profile_image.url
            if request and not url.startswith(('http://', 'https://')):
                return request.build_absolute_uri(url)
            return url
        return None

    def get_cover_image_url(self, obj):
        request = self.context.get('request')
        if obj.cover_image:
            url = obj.cover_image.url
            if request and not url.startswith(('http://', 'https://')):
                return request.build_absolute_uri(url)
            return url
        return None
