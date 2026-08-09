from django.contrib import admin
from .models import Project, ProjectImage, ProjectLike, ProjectComment


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    Expose user projects with detailed categories, creator name,
    featured status, and engagement metrics.
    """
    list_display = ('title', 'owner', 'category', 'is_featured', 'get_likes_count', 'get_comments_count', 'created_at')
    list_filter = ('category', 'is_featured', 'created_at')
    search_fields = ('title', 'owner__email', 'owner__first_name', 'owner__last_name', 'short_description')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ProjectImageInline]

    def get_likes_count(self, obj):
        return obj.likes.count()
    get_likes_count.short_description = 'Likes'

    def get_comments_count(self, obj):
        return obj.comments.count()
    get_comments_count.short_description = 'Comments'


@admin.register(ProjectImage)
class ProjectImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'project', 'caption', 'created_at')
    search_fields = ('project__title', 'caption')


@admin.register(ProjectLike)
class ProjectLikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'project', 'created_at')
    search_fields = ('user__email', 'project__title')


@admin.register(ProjectComment)
class ProjectCommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'project', 'created_at')
    search_fields = ('user__email', 'project__title', 'content')
