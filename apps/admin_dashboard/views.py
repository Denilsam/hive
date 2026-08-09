import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.sessions.models import Session

import logging
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.cache import cache

logger = logging.getLogger(__name__)

from .models import (
    AdminProfile, AdminPermission, AdminUserPermission,
    Report, AdminActivityLog, PlatformSettings
)
from .forms import PlatformSettingsForm
from .permissions import PermissionRequiredMixin, AdminRequiredMixin, SuperAdminRequiredMixin
from .services import log_admin_activity

def safe_delete_file(field_file):
    if field_file and hasattr(field_file, 'storage') and hasattr(field_file, 'name') and field_file.name:
        try:
            if field_file.storage.exists(field_file.name):
                field_file.storage.delete(field_file.name)
        except Exception:
            pass

from apps.posts.models import Post, Comment
from apps.connections.models import Connection

from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from apps.portfolio.models import Project
from apps.marketplace.models import Collaboration
from apps.connections.models import Follow
from apps.chat.models import Message

User = get_user_model()


class AdminLoginView(View):
    template_name = 'admin_dashboard/login.html'

    def get(self, request):
        if request.user.is_authenticated and request.user.is_superuser:
            return redirect('admin_dashboard:dashboard')
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')

        user = authenticate(request, username=email, password=password)
        if user is not None:
            if user.is_superuser:
                auth_login(request, user)
                messages.success(request, f"Welcome to Superadmin Dashboard, {user.first_name or user.email}!")
                return redirect('admin_dashboard:dashboard')
            else:
                messages.error(request, "Access denied. Only Superadmin accounts can log in here.")
                return render(request, self.template_name, {'email': email})
        else:
            messages.error(request, "Invalid admin credentials.")
            return render(request, self.template_name, {'email': email})


class AdminLogoutView(View):
    def post(self, request):
        if request.user.is_authenticated:
            auth_logout(request)
            messages.success(request, "Superadmin logged out successfully.")
        return redirect('admin_dashboard:admin_login')

    def get(self, request):
        return self.post(request)


class DashboardView(AdminRequiredMixin, View):
    template_name = 'admin_dashboard/dashboard.html'

    def get(self, request):
        today = timezone.now().date()
        week_ago = today - datetime.timedelta(days=7)

        # Exclude superadmin accounts from Connect user counts
        connect_users = User.objects.filter(is_superuser=False)
        total_users = connect_users.count()
        verified_users = connect_users.filter(is_verified=True).count()
        active_users = connect_users.filter(is_active=True).count()
        suspended_users = connect_users.filter(is_active=False).count()

        total_posts = Post.objects.count() if hasattr(Post, 'objects') else 0
        total_projects = Project.objects.count() if hasattr(Project, 'objects') else 0
        total_collaborations = Collaboration.objects.count() if hasattr(Collaboration, 'objects') else 0
        total_follows = Follow.objects.count() if hasattr(Follow, 'objects') else 0
        total_messages = Message.objects.count() if hasattr(Message, 'objects') else 0
        total_connections = Connection.objects.count() if hasattr(Connection, 'objects') else 0
        pending_reports = Report.objects.filter(status=Report.Status.PENDING).count()
        new_users_week = connect_users.filter(date_joined__gte=week_ago).count()

        # Growth stats (last 7 days registration counts)
        registration_days = []
        registration_counts = []
        for i in range(6, -1, -1):
            day = today - datetime.timedelta(days=i)
            cnt = connect_users.filter(date_joined__date=day).count()
            registration_days.append(day.strftime('%b %d'))
            registration_counts.append(cnt)

        # Account type distribution
        account_types_data = connect_users.values('account_type').annotate(count=Count('id'))

        recent_users = connect_users.order_by('-date_joined')[:5]
        recent_reports = Report.objects.order_by('-created_at')[:5]
        recent_logs = AdminActivityLog.objects.order_by('-created_at')[:5]

        context = {
            'total_users': total_users,
            'verified_users': verified_users,
            'active_users': active_users,
            'suspended_users': suspended_users,
            'total_posts': total_posts,
            'total_projects': total_projects,
            'total_collaborations': total_collaborations,
            'total_follows': total_follows,
            'total_messages': total_messages,
            'total_connections': total_connections,
            'pending_reports': pending_reports,
            'new_users_week': new_users_week,
            'registration_days': registration_days,
            'registration_counts': registration_counts,
            'account_types_data': account_types_data,
            'recent_users': recent_users,
            'recent_reports': recent_reports,
            'recent_logs': recent_logs,
        }
        return render(request, self.template_name, context)


class UserListView(PermissionRequiredMixin, View):
    permission_required_codename = 'manage_users'
    template_name = 'admin_dashboard/users.html'

    def get(self, request):
        users = User.objects.all().order_by('-date_joined')

        search_query = request.GET.get('q', '').strip()
        account_type = request.GET.get('account_type', '').strip()
        status = request.GET.get('status', '').strip()

        if search_query:
            users = users.filter(
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(username__icontains=search_query)
            )

        if account_type:
            users = users.filter(account_type=account_type)

        if status == 'verified':
            users = users.filter(is_verified=True)
        elif status == 'unverified':
            users = users.filter(is_verified=False)
        elif status == 'active':
            users = users.filter(is_active=True)
        elif status == 'suspended':
            users = users.filter(is_active=False)

        context = {
            'users': users[:100],  # Cap display at 100
            'search_query': search_query,
            'selected_account_type': account_type,
            'selected_status': status,
        }
        return render(request, self.template_name, context)


class UserDetailView(PermissionRequiredMixin, View):
    permission_required_codename = 'manage_users'
    template_name = 'admin_dashboard/user_detail.html'

    def get(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)
        user_posts = target_user.posts.all().order_by('-created_at')[:10] if hasattr(target_user, 'posts') else []
        reports_filed = Report.objects.filter(reporter=target_user).count()
        reports_against = Report.objects.filter(reported_user=target_user).count()

        superadmin_count = User.objects.filter(is_superuser=True).count()
        is_self = (request.user.pk == target_user.pk)
        
        # Determine if current user can delete target_user
        if is_self:
            can_delete = False
            cannot_delete_reason = "You cannot delete your own account."
        elif target_user.is_superuser:
            if not request.user.is_superuser:
                can_delete = False
                cannot_delete_reason = "Only a Superadmin can delete another Superadmin."
            elif superadmin_count <= 1:
                can_delete = False
                cannot_delete_reason = "At least one Super Admin must remain on the platform."
            else:
                can_delete = True
                cannot_delete_reason = None
        else:
            can_delete = True
            cannot_delete_reason = None

        context = {
            'target_user': target_user,
            'user_posts': user_posts,
            'reports_filed': reports_filed,
            'reports_against': reports_against,
            'superadmin_count': superadmin_count,
            'is_self': is_self,
            'can_delete': can_delete,
            'cannot_delete_reason': cannot_delete_reason,
        }
        return render(request, self.template_name, context)


from django.db import transaction

class UserSuspendView(PermissionRequiredMixin, View):
    permission_required_codename = 'suspend_users'

    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)

        # Self-suspension check
        if target_user == request.user:
            messages.error(request, "You cannot suspend your own account.")
            return redirect('admin_dashboard:user_detail', pk=pk)

        # Superadmin suspension check (at least 1 active superadmin must remain)
        if target_user.is_superuser:
            if not request.user.is_superuser:
                messages.error(request, "Only a Superadmin can suspend another Superadmin.")
                return redirect('admin_dashboard:user_detail', pk=pk)
            active_su_count = User.objects.filter(is_superuser=True, is_active=True).count()
            if active_su_count <= 1:
                messages.error(request, "At least one active Super Admin must remain on the platform.")
                return redirect('admin_dashboard:user_detail', pk=pk)

        target_user.is_active = False
        target_user.save()
        log_admin_activity(request, f"Suspended user {target_user.email}", target=target_user.id)
        messages.success(request, f"User {target_user.email} has been suspended.")
        return redirect('admin_dashboard:user_detail', pk=pk)


class UserReactivateView(PermissionRequiredMixin, View):
    permission_required_codename = 'suspend_users'

    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)
        target_user.is_active = True
        target_user.save()
        log_admin_activity(request, f"Reactivated user {target_user.email}", target=target_user.id)
        messages.success(request, f"User {target_user.email} has been reactivated.")
        return redirect('admin_dashboard:user_detail', pk=pk)


class UserDeleteView(PermissionRequiredMixin, View):
    permission_required_codename = 'delete_users'

    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)

        # Self-delete check
        if target_user == request.user:
            messages.error(request, "You cannot soft delete your own account.")
            return redirect('admin_dashboard:user_detail', pk=pk)

        # Superadmin soft delete check
        if target_user.is_superuser:
            if not request.user.is_superuser:
                messages.error(request, "Only a Superadmin can soft delete another Superadmin.")
                return redirect('admin_dashboard:user_detail', pk=pk)
            active_su_count = User.objects.filter(is_superuser=True, is_active=True).count()
            if active_su_count <= 1:
                messages.error(request, "At least one active Super Admin must remain on the platform.")
                return redirect('admin_dashboard:user_detail', pk=pk)
        elif not request.user.is_superuser and target_user.is_staff:
            messages.error(request, "You do not have permission to delete administrative accounts.")
            return redirect('admin_dashboard:user_detail', pk=pk)

        # Soft delete: deactivate user
        target_user.is_active = False
        target_user.save()
        log_admin_activity(request, f"Soft deleted user {target_user.email}", target=target_user.id)
        messages.success(request, f"User {target_user.email} soft deleted (deactivated).")
        return redirect('admin_dashboard:user_list')


class UserPermanentDeleteView(PermissionRequiredMixin, View):
    permission_required_codename = 'permanently_delete_users'

    def post(self, request, pk):
        # Prevent self-deletion
        if request.user.pk == pk:
            messages.error(request, "You cannot permanently delete your own Super Admin account.")
            return redirect('admin_dashboard:user_detail', pk=pk)

        with transaction.atomic():
            target_user = get_object_or_404(User.objects.select_for_update(), pk=pk)

            if target_user.is_superuser:
                if not request.user.is_superuser:
                    messages.error(request, "Only a Superadmin can permanently delete another Superadmin.")
                    return redirect('admin_dashboard:user_detail', pk=pk)

                su_count = User.objects.filter(is_superuser=True).select_for_update().count()
                if su_count <= 1:
                    messages.error(request, "The last remaining Super Admin account cannot be deleted.")
                    return redirect('admin_dashboard:user_detail', pk=pk)
            elif not request.user.is_superuser and target_user.is_staff:
                messages.error(request, "You do not have permission to permanently delete administrative accounts.")
                return redirect('admin_dashboard:user_detail', pk=pk)

            user_email = target_user.email
            is_target_su = target_user.is_superuser
            target_user.delete()

            log_action = "SUPERADMIN_PERMANENT_DELETE" if is_target_su else f"PERMANENTLY deleted user {user_email}"
            log_admin_activity(request, f"{log_action}: {user_email}", target=pk)

        messages.success(request, f"Account {user_email} permanently deleted successfully.")
        return redirect('admin_dashboard:user_list')


class PostModerationListView(PermissionRequiredMixin, View):
    permission_required_codename = 'manage_posts'
    template_name = 'admin_dashboard/posts.html'

    def get(self, request):
        posts = Post.objects.all().order_by('-created_at') if hasattr(Post, 'objects') else []
        search_query = request.GET.get('q', '').strip()
        if search_query and posts:
            posts = posts.filter(Q(content__icontains=search_query) | Q(author__email__icontains=search_query))
        
        context = {
            'posts': posts[:100] if posts else [],
            'search_query': search_query,
        }
        return render(request, self.template_name, context)


class PostDeleteView(PermissionRequiredMixin, View):
    permission_required_codename = 'manage_posts'

    def post(self, request, pk):
        post_obj = get_object_or_404(Post, pk=pk)
        post_id = post_obj.id
        post_obj.delete()
        log_admin_activity(request, f"Deleted post {post_id}", target=post_id)
        messages.success(request, f"Post #{post_id} deleted successfully.")
        return redirect('admin_dashboard:post_list')


class PortfolioModerationListView(PermissionRequiredMixin, View):
    permission_required_codename = 'manage_posts'
    template_name = 'admin_dashboard/portfolio.html'

    def get(self, request):
        projects = Project.objects.select_related('owner').order_by('-created_at')
        search_query = request.GET.get('q', '').strip()
        if search_query:
            projects = projects.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(owner__email__icontains=search_query)
            )

        context = {
            'projects': projects[:100],
            'search_query': search_query,
        }
        return render(request, self.template_name, context)


class PortfolioDeleteView(PermissionRequiredMixin, View):
    permission_required_codename = 'manage_posts'

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        title = project.title
        project.delete()
        log_admin_activity(request, f"Deleted portfolio project '{title}' (#{pk})", target=pk)
        messages.success(request, f"Portfolio project '{title}' deleted successfully.")
        return redirect('admin_dashboard:portfolio_list')


class MarketplaceModerationListView(PermissionRequiredMixin, View):
    permission_required_codename = 'manage_posts'
    template_name = 'admin_dashboard/marketplace.html'

    def get(self, request):
        collaborations = Collaboration.objects.select_related('creator').order_by('-created_at')
        search_query = request.GET.get('q', '').strip()
        if search_query:
            collaborations = collaborations.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(creator__email__icontains=search_query)
            )

        context = {
            'collaborations': collaborations[:100],
            'search_query': search_query,
        }
        return render(request, self.template_name, context)


class MarketplaceDeleteView(PermissionRequiredMixin, View):
    permission_required_codename = 'manage_posts'

    def post(self, request, pk):
        collab = get_object_or_404(Collaboration, pk=pk)
        title = collab.title
        collab.delete()
        log_admin_activity(request, f"Deleted marketplace opportunity '{title}' (#{pk})", target=pk)
        messages.success(request, f"Marketplace opportunity '{title}' deleted successfully.")
        return redirect('admin_dashboard:marketplace_list')


class ReportListView(PermissionRequiredMixin, View):
    permission_required_codename = 'manage_reports'
    template_name = 'admin_dashboard/reports.html'

    def get(self, request):
        reports = Report.objects.all().order_by('-created_at')
        status_filter = request.GET.get('status', '').strip()
        if status_filter:
            reports = reports.filter(status=status_filter)

        context = {
            'reports': reports,
            'selected_status': status_filter,
            'status_choices': Report.Status.choices,
        }
        return render(request, self.template_name, context)


class ReportActionView(PermissionRequiredMixin, View):
    permission_required_codename = 'manage_reports'

    def post(self, request, pk):
        report = get_object_or_404(Report, pk=pk)
        new_status = request.POST.get('status')
        action_note = request.POST.get('action_note', '')

        if new_status in [Report.Status.RESOLVED, Report.Status.REJECTED, Report.Status.REVIEWING]:
            report.status = new_status
            if new_status == Report.Status.RESOLVED:
                report.resolved_at = timezone.now()
                report.resolved_by = request.user
            report.save()

            log_admin_activity(request, f"Updated report #{report.id} to {new_status}. Note: {action_note}", target=report.id)
            messages.success(request, f"Report status updated to {new_status}.")
        return redirect('admin_dashboard:report_list')


class AnalyticsDashboardView(PermissionRequiredMixin, View):
    permission_required_codename = 'view_analytics'
    template_name = 'admin_dashboard/analytics.html'

    def get(self, request):
        today = timezone.now().date()
        daily_counts = [User.objects.filter(date_joined__date=today - datetime.timedelta(days=i)).count() for i in range(14)]
        daily_labels = [(today - datetime.timedelta(days=i)).strftime('%b %d') for i in range(14)]
        daily_counts.reverse()
        daily_labels.reverse()

        most_active_users = User.objects.annotate(post_count=Count('posts')).order_by('-post_count')[:5] if hasattr(User, 'posts') else []

        context = {
            'daily_counts': daily_counts,
            'daily_labels': daily_labels,
            'most_active_users': most_active_users,
            'total_users': User.objects.count(),
            'total_posts': Post.objects.count() if hasattr(Post, 'objects') else 0,
        }
        return render(request, self.template_name, context)


class AdminManagementListView(PermissionRequiredMixin, View):
    permission_required_codename = 'manage_admins'
    template_name = 'admin_dashboard/admins.html'

    def get(self, request):
        admin_profiles = AdminProfile.objects.select_related('user').all()
        all_permissions = AdminPermission.objects.all()

        # Seed default admin permissions if none exist
        if not all_permissions.exists():
            default_perms = [
                ('manage_users', 'Manage Users', 'Can list, filter and view users'),
                ('suspend_users', 'Suspend Users', 'Can suspend and reactivate users'),
                ('delete_users', 'Delete Users', 'Can soft delete user accounts'),
                ('permanently_delete_users', 'Permanently Delete Users', 'Can permanently remove user accounts'),
                ('manage_posts', 'Manage Posts', 'Can delete offensive posts'),
                ('manage_comments', 'Manage Comments', 'Can delete comments'),
                ('manage_reports', 'Manage Reports', 'Can review and resolve user reports'),
                ('view_analytics', 'View Analytics', 'Can access platform analytics dashboard'),
                ('manage_admins', 'Manage Admins', 'Can add and modify admin roles'),
                ('manage_settings', 'Manage Settings', 'Can update platform settings'),
                ('view_activity_logs', 'View Activity Logs', 'Can view audit trail'),
                ('manage_sessions', 'Manage Sessions', 'Can terminate active admin sessions'),
            ]
            for code, name, desc in default_perms:
                AdminPermission.objects.get_or_create(codename=code, defaults={'name': name, 'description': desc})
            all_permissions = AdminPermission.objects.all()

        context = {
            'admin_profiles': admin_profiles,
            'all_permissions': all_permissions,
        }
        return render(request, self.template_name, context)


class RoleManagementView(SuperAdminRequiredMixin, View):
    template_name = 'admin_dashboard/roles.html'

    def get(self, request):
        users = User.objects.filter(is_superuser=False).order_by('-date_joined')
        search_query = request.GET.get('q', '').strip()
        role_filter = request.GET.get('role', '').strip()

        if search_query:
            users = users.filter(
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(username__icontains=search_query)
            )

        if role_filter == 'ADMIN':
            users = users.filter(is_staff=True)
        elif role_filter == 'USER':
            users = users.filter(is_staff=False)

        context = {
            'users': users[:100],
            'search_query': search_query,
            'selected_role': role_filter,
        }
        return render(request, self.template_name, context)


class RoleUpdateView(SuperAdminRequiredMixin, View):
    def post(self, request, pk):
        target_user = get_object_or_404(User, pk=pk)

        # Reject modifying superuser accounts via role management
        if target_user.is_superuser or target_user == request.user:
            messages.error(request, "Superadmin account roles cannot be modified.")
            return redirect('admin_dashboard:role_list')

        new_role = request.POST.get('role', '').strip().upper()

        if new_role == 'ADMIN':
            target_user.is_staff = True
            target_user.account_type = 'ADMIN'
            target_user.save()
            log_admin_activity(request, f"Promoted user {target_user.email} to ADMIN role", target=target_user.id)
            messages.success(request, f"{target_user.first_name or target_user.email} has been promoted to ADMIN.")
        elif new_role == 'USER':
            target_user.is_staff = False
            if target_user.account_type == 'ADMIN':
                target_user.account_type = 'STUDENT'
            target_user.save()
            log_admin_activity(request, f"Demoted user {target_user.email} to USER role", target=target_user.id)
            messages.success(request, f"{target_user.first_name or target_user.email} has been demoted to USER.")
        else:
            messages.error(request, "Invalid role selection.")

        return redirect('admin_dashboard:role_list')


class AdminCreateView(PermissionRequiredMixin, View):
    permission_required_codename = 'manage_admins'
    template_name = 'admin_dashboard/admin_form.html'

    def get(self, request):
        non_admins = User.objects.filter(admin_profile__isnull=True)
        permissions = AdminPermission.objects.all()
        roles = [
            (AdminProfile.Role.ADMIN_ASSISTANT, 'Admin Assistant'),
            (AdminProfile.Role.CONTENT_MODERATOR, 'Content Moderator'),
            (AdminProfile.Role.SUPPORT_ADMIN, 'Support Admin'),
        ]
        return render(request, self.template_name, {'non_admins': non_admins, 'permissions': permissions, 'roles': roles})

    def post(self, request):
        user_id = request.POST.get('user_id')
        role = request.POST.get('role')
        permission_ids = request.POST.getlist('permissions')

        user_obj = get_object_or_404(User, pk=user_id)
        
        # Enforce rule: SUPER_ADMIN role cannot be assigned directly
        if role == AdminProfile.Role.SUPER_ADMIN:
            messages.error(request, "Super Admin role cannot be assigned.")
            return redirect('admin_dashboard:admin_create')

        profile, created = AdminProfile.objects.get_or_create(
            user=user_obj,
            defaults={'role': role, 'created_by': request.user, 'is_active': True}
        )

        if not created:
            profile.role = role
            profile.is_active = True
            profile.save()

        user_obj.is_staff = True
        user_obj.save()

        # Update permissions
        AdminUserPermission.objects.filter(admin_profile=profile).delete()
        for perm_id in permission_ids:
            perm = AdminPermission.objects.filter(pk=perm_id).first()
            if perm:
                AdminUserPermission.objects.create(admin_profile=profile, permission=perm)

        log_admin_activity(request, f"Created/Updated admin {user_obj.email} with role {role}", target=profile.id)
        messages.success(request, f"Admin profile created for {user_obj.email}.")
        return redirect('admin_dashboard:admin_list')


class AdminPermissionsEditView(PermissionRequiredMixin, View):
    permission_required_codename = 'manage_admins'
    template_name = 'admin_dashboard/permissions.html'

    def get(self, request, pk):
        profile = get_object_or_404(AdminProfile, pk=pk)
        all_permissions = AdminPermission.objects.all()
        assigned_perm_ids = profile.user_permissions.values_list('permission_id', flat=True)

        context = {
            'profile': profile,
            'all_permissions': all_permissions,
            'assigned_perm_ids': assigned_perm_ids,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk):
        profile = get_object_or_404(AdminProfile, pk=pk)
        
        # Guard: Super Admin permissions cannot be modified or downgraded
        if profile.role == AdminProfile.Role.SUPER_ADMIN:
            messages.error(request, "Super Admin permissions cannot be modified.")
            return redirect('admin_dashboard:admin_list')

        permission_ids = request.POST.getlist('permissions')
        AdminUserPermission.objects.filter(admin_profile=profile).delete()
        for perm_id in permission_ids:
            perm = AdminPermission.objects.filter(pk=perm_id).first()
            if perm:
                AdminUserPermission.objects.create(admin_profile=profile, permission=perm)

        log_admin_activity(request, f"Updated permissions for admin {profile.user.email}", target=profile.id)
        messages.success(request, f"Permissions updated for {profile.user.email}.")
        return redirect('admin_dashboard:admin_list')


class ActivityLogListView(PermissionRequiredMixin, View):
    permission_required_codename = 'view_activity_logs'
    template_name = 'admin_dashboard/activity_logs.html'

    def get(self, request):
        logs = AdminActivityLog.objects.all()
        admin_filter = request.GET.get('admin', '').strip()
        if admin_filter:
            logs = logs.filter(admin__email__icontains=admin_filter)

        context = {
            'logs': logs[:200],  # Cap output to 200 logs
            'admin_filter': admin_filter,
        }
        return render(request, self.template_name, context)


class SessionsView(PermissionRequiredMixin, View):
    permission_required_codename = 'manage_sessions'
    template_name = 'admin_dashboard/sessions.html'

    def get(self, request):
        active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        context = {
            'active_sessions_count': active_sessions.count(),
        }
        return render(request, self.template_name, context)


class PlatformSettingsView(PermissionRequiredMixin, View):
    permission_required_codename = 'manage_settings'
    template_name = 'admin_dashboard/settings.html'

    def get(self, request):
        settings_obj = PlatformSettings.load()
        form = PlatformSettingsForm(instance=settings_obj)
        context = {
            'settings_obj': settings_obj,
            'form': form,
        }
        return render(request, self.template_name, context)

    def post(self, request):
        settings_obj = PlatformSettings.load()
        action = request.POST.get('action')

        if action == 'reset_logo':
            if settings_obj.logo:
                safe_delete_file(settings_obj.logo)
                settings_obj.logo = None
                settings_obj.updated_by = request.user
                settings_obj.save()
                log_admin_activity(request, "Reset primary logo to default", target="PlatformSettings")
                messages.success(request, "Primary logo reset to default.")
            return redirect('admin_dashboard:settings')

        if action == 'reset_favicon':
            if settings_obj.favicon:
                safe_delete_file(settings_obj.favicon)
                settings_obj.favicon = None
                settings_obj.updated_by = request.user
                settings_obj.save()
                log_admin_activity(request, "Reset favicon to default", target="PlatformSettings")
                messages.success(request, "Favicon reset to default.")
            return redirect('admin_dashboard:settings')

        if action == 'reset_admin_logo':
            if settings_obj.admin_logo:
                safe_delete_file(settings_obj.admin_logo)
                settings_obj.admin_logo = None
                settings_obj.updated_by = request.user
                settings_obj.save()
                log_admin_activity(request, "Reset admin logo to default", target="PlatformSettings")
                messages.success(request, "Admin logo reset to default.")
            return redirect('admin_dashboard:settings')

        # Keep existing file objects for potential cleanup
        old_logo = settings_obj.logo
        old_favicon = settings_obj.favicon
        old_admin_logo = settings_obj.admin_logo

        form = PlatformSettingsForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            updated_settings = form.save(commit=False)
            updated_settings.updated_by = request.user

            # Delete old file from storage if a new one is uploaded
            if 'logo' in request.FILES and old_logo and old_logo != updated_settings.logo:
                safe_delete_file(old_logo)
            if 'favicon' in request.FILES and old_favicon and old_favicon != updated_settings.favicon:
                safe_delete_file(old_favicon)
            if 'admin_logo' in request.FILES and old_admin_logo and old_admin_logo != updated_settings.admin_logo:
                safe_delete_file(old_admin_logo)

            updated_settings.save()
            log_admin_activity(request, "Updated Platform Settings & Branding", target="PlatformSettings")
            messages.success(request, "Platform settings and branding updated successfully.")
            return redirect('admin_dashboard:settings')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {error}")
            context = {
                'settings_obj': settings_obj,
                'form': form,
            }
            return render(request, self.template_name, context)


class AdminForgotPasswordView(View):
    template_name = 'admin_dashboard/forgot_password.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        email = request.POST.get('email', '').strip().lower()
        if not email:
            messages.error(request, "Please enter a valid email address.")
            return render(request, self.template_name)

        # Rate limiting: Max 5 password reset requests per 15 minutes per IP
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '127.0.0.1')).split(',')[0].strip()
        cache_key = f"admin_pw_reset_rate_{client_ip}"
        request_count = cache.get(cache_key, 0)
        if request_count >= 5:
            messages.error(request, "Too many password reset requests. Please wait a few minutes before trying again.")
            return render(request, self.template_name, {'email': email})

        cache.set(cache_key, request_count + 1, timeout=900)

        # Find user and check if user is an authorized Hive Admin
        user = User.objects.filter(email__iexact=email).first()
        is_eligible_admin = False
        if user and user.is_active:
            if user.is_superuser or user.is_staff:
                is_eligible_admin = True
            elif hasattr(user, 'admin_profile') and user.admin_profile.is_active:
                is_eligible_admin = True

        if is_eligible_admin:
            try:
                token = default_token_generator.make_token(user)
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                reset_path = reverse('admin_dashboard:admin_password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})
                reset_url = request.build_absolute_uri(reset_path)

                platform_settings = PlatformSettings.load()
                logo_url = request.build_absolute_uri(platform_settings.logo_url)
                email_context = {
                    'reset_url': reset_url,
                    'site_name': platform_settings.site_name,
                    'logo_url': logo_url,
                    'user': user,
                }

                subject = "Hive Admin Password Reset"
                html_body = render_to_string('admin_dashboard/emails/admin_password_reset_email.html', email_context)
                text_body = render_to_string('admin_dashboard/emails/admin_password_reset_email.txt', email_context)
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Hive Admin <noreply@hive.com>')

                msg = EmailMultiAlternatives(subject, text_body, from_email, [user.email])
                msg.attach_alternative(html_body, "text/html")
                msg.send()
            except Exception as e:
                logger.error(f"Failed to send Admin Password Reset Email to {email}: {e}")

        # Account enumeration protection: return generic message regardless of email existence or admin status
        messages.info(request, "If an eligible admin account exists for this email, a password reset link has been sent.")
        return render(request, self.template_name, {'email': email})


class AdminResetPasswordConfirmView(View):
    template_name = 'admin_dashboard/reset_password.html'

    def get_user_from_uidb64(self, uidb64):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
            if user and user.is_active:
                if user.is_superuser or user.is_staff or (hasattr(user, 'admin_profile') and user.admin_profile.is_active):
                    return user
        except Exception:
            pass
        return None

    def get(self, request, uidb64, token):
        user = self.get_user_from_uidb64(uidb64)
        validlink = False
        token_error = ""

        if user is not None and default_token_generator.check_token(user, token):
            validlink = True
        else:
            token_error = "This password reset link is no longer valid or has expired. Please request a new one."

        return render(request, self.template_name, {
            'validlink': validlink,
            'token_error': token_error,
            'uidb64': uidb64,
            'token': token,
        })

    def post(self, request, uidb64, token):
        user = self.get_user_from_uidb64(uidb64)
        if user is None or not default_token_generator.check_token(user, token):
            return render(request, self.template_name, {
                'validlink': False,
                'token_error': "This password reset link is no longer valid or has expired. Please request a new one.",
                'uidb64': uidb64,
                'token': token,
            })

        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not password1 or not password2:
            messages.error(request, "Please enter both password fields.")
            return render(request, self.template_name, {'validlink': True, 'uidb64': uidb64, 'token': token})

        if password1 != password2:
            messages.error(request, "Passwords do not match. Please try again.")
            return render(request, self.template_name, {'validlink': True, 'uidb64': uidb64, 'token': token})

        try:
            validate_password(password1, user=user)
        except ValidationError as errors:
            for err in errors.messages:
                messages.error(request, err)
            return render(request, self.template_name, {'validlink': True, 'uidb64': uidb64, 'token': token})

        # Update password. This updates password hash in DB, invalidating reset token & active user sessions
        user.set_password(password1)
        user.save()

        try:
            log_admin_activity(request, "Admin Password Reset Completed", target=f"User:{user.email}")
        except Exception:
            pass

        return redirect('admin_dashboard:admin_password_reset_done')


class AdminResetPasswordDoneView(View):
    template_name = 'admin_dashboard/reset_password_success.html'

    def get(self, request):
        return render(request, self.template_name)


