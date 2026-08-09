from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from .models import AdminProfile, AdminUserPermission, AdminPermission

def get_admin_profile(user):
    if not user.is_authenticated:
        return None
    try:
        return user.admin_profile
    except AdminProfile.DoesNotExist:
        # Automatically make first superuser the SUPER_ADMIN if no admin profile exists yet
        if user.is_superuser:
            profile = AdminProfile.objects.create(
                user=user,
                role=AdminProfile.Role.SUPER_ADMIN,
                is_active=True
            )
            return profile
        return None

def has_admin_permission(user, permission_codename):
    if not user.is_authenticated:
        return False
    
    profile = get_admin_profile(user)
    if not profile or not profile.is_active:
        return False
    
    # Super Admin bypasses all checks
    if profile.role == AdminProfile.Role.SUPER_ADMIN or user.is_superuser:
        return True
    
    return AdminUserPermission.objects.filter(
        admin_profile=profile,
        permission__codename=permission_codename
    ).exists()

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, "Access denied. Administrative privileges required.")
            return redirect('admin_dashboard:admin_login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def superadmin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            messages.error(request, "Access denied. Superadmin privileges required.")
            return redirect('admin_dashboard:dashboard' if request.user.is_authenticated else 'admin_dashboard:admin_login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def permission_required(permission_codename):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated or not (request.user.is_superuser or request.user.is_staff):
                messages.error(request, "Access denied. Administrative privileges required.")
                return redirect('admin_dashboard:admin_login')
            if not has_admin_permission(request.user, permission_codename):
                messages.error(request, f"Permission denied: Requires '{permission_codename}' permission.")
                return redirect('admin_dashboard:dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

class AdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not (request.user.is_superuser or request.user.is_staff):
            messages.error(request, "Access denied. Administrative privileges required.")
            return redirect('admin_dashboard:admin_login')
        return super().dispatch(request, *args, **kwargs)

class SuperAdminRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superuser:
            messages.error(request, "Access denied. Superadmin privileges required.")
            return redirect('admin_dashboard:dashboard' if request.user.is_authenticated else 'admin_dashboard:admin_login')
        return super().dispatch(request, *args, **kwargs)

class PermissionRequiredMixin(AdminRequiredMixin):
    permission_required_codename = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if self.permission_required_codename:
            if not has_admin_permission(request.user, self.permission_required_codename):
                messages.error(request, f"Permission denied: Requires '{self.permission_required_codename}' permission.")
                return redirect('admin_dashboard:dashboard')
        return super().dispatch(request, *args, **kwargs)
