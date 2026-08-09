from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('login/', views.AdminLoginView.as_view(), name='admin_login'),
    path('logout/', views.AdminLogoutView.as_view(), name='admin_logout'),
    path('forgot-password/', views.AdminForgotPasswordView.as_view(), name='admin_forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.AdminResetPasswordConfirmView.as_view(), name='admin_password_reset_confirm'),
    path('reset-password/done/', views.AdminResetPasswordDoneView.as_view(), name='admin_password_reset_done'),
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user_detail'),
    path('users/<int:pk>/suspend/', views.UserSuspendView.as_view(), name='user_suspend'),
    path('users/<int:pk>/reactivate/', views.UserReactivateView.as_view(), name='user_reactivate'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('users/<int:pk>/permanent-delete/', views.UserPermanentDeleteView.as_view(), name='user_permanent_delete'),
    path('posts/', views.PostModerationListView.as_view(), name='post_list'),
    path('posts/<int:pk>/delete/', views.PostDeleteView.as_view(), name='post_delete'),
    path('portfolio/', views.PortfolioModerationListView.as_view(), name='portfolio_list'),
    path('portfolio/<int:pk>/delete/', views.PortfolioDeleteView.as_view(), name='portfolio_delete'),
    path('marketplace/', views.MarketplaceModerationListView.as_view(), name='marketplace_list'),
    path('marketplace/<int:pk>/delete/', views.MarketplaceDeleteView.as_view(), name='marketplace_delete'),
    path('reports/', views.ReportListView.as_view(), name='report_list'),
    path('reports/<uuid:pk>/action/', views.ReportActionView.as_view(), name='report_action'),
    path('analytics/', views.AnalyticsDashboardView.as_view(), name='analytics'),
    path('admins/', views.AdminManagementListView.as_view(), name='admin_list'),
    path('admins/create/', views.AdminCreateView.as_view(), name='admin_create'),
    path('roles/', views.RoleManagementView.as_view(), name='role_list'),
    path('roles/<int:pk>/update/', views.RoleUpdateView.as_view(), name='role_update'),
    path('admins/<uuid:pk>/permissions/', views.AdminPermissionsEditView.as_view(), name='admin_permissions'),
    path('activity-logs/', views.ActivityLogListView.as_view(), name='activity_logs'),
    path('settings/', views.PlatformSettingsView.as_view(), name='settings'),
    path('sessions/', views.SessionsView.as_view(), name='sessions'),
]
