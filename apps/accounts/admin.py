from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, AuthLandingImage


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Expose custom User model details, searches, and filters in the Django Admin.
    """
    list_display = ('email', 'first_name', 'last_name', 'account_type', 'is_verified', 'profile_completed', 'is_staff')
    list_filter = ('account_type', 'is_verified', 'profile_completed', 'is_staff', 'is_superuser')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    
    # Custom edit field sets (email-based login)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'username')}),
        ('Custom Account Status', {'fields': ('account_type', 'is_verified', 'profile_completed')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Fields shown during creation
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password', 'first_name', 'last_name', 'account_type', 'is_verified', 'profile_completed'),
        }),
    )


@admin.register(AuthLandingImage)
class AuthLandingImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'display_order')
    list_filter = ('is_active',)
    search_fields = ('title', 'description')
    ordering = ('display_order', 'id')

