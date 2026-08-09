from django.contrib import admin
from .models import Profile, Education, Experience, Skill, UserSkill, Certificate


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Expose user profiles with location, account type details,
    and profile completion percentages.
    """
    list_display = ('user', 'get_account_type', 'location', 'get_completion_percentage', 'created_at')
    list_filter = ('user__account_type', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'location', 'headline')

    def get_account_type(self, obj):
        return obj.user.get_account_type_display() if obj.user.account_type else 'None'
    get_account_type.short_description = 'Account Type'

    def get_completion_percentage(self, obj):
        return f"{obj.completion_percentage}%"
    get_completion_percentage.short_description = 'Completion %'


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ('user', 'degree', 'institution', 'start_year', 'end_year')
    search_fields = ('user__email', 'degree', 'institution')


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'role', 'employment_type', 'start_date', 'end_date')
    list_filter = ('employment_type', 'currently_working')
    search_fields = ('user__email', 'company_name', 'role')


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(UserSkill)
class UserSkillAdmin(admin.ModelAdmin):
    list_display = ('user', 'skill', 'level')
    list_filter = ('level',)
    search_fields = ('user__email', 'skill__name')


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'organization', 'issue_date')
    search_fields = ('user__email', 'title', 'organization')
