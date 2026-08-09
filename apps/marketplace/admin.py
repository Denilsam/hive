from django.contrib import admin
from .models import Collaboration, CollaborationSkill, CollaborationApplication

@admin.register(Collaboration)
class CollaborationAdmin(admin.ModelAdmin):
    list_display = ('title', 'creator', 'project_type', 'budget_type', 'status', 'created_at')
    list_filter = ('project_type', 'budget_type', 'status')
    search_fields = ('title', 'description', 'category')


@admin.register(CollaborationSkill)
class CollaborationSkillAdmin(admin.ModelAdmin):
    list_display = ('collaboration', 'skill')
    search_fields = ('collaboration__title', 'skill__name')


@admin.register(CollaborationApplication)
class CollaborationApplicationAdmin(admin.ModelAdmin):
    list_display = ('collaboration', 'applicant', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('collaboration__title', 'applicant__email')
