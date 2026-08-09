from django.urls import path
from .views import (
    RegisterView, VerifyEmailPendingView, ResendVerificationView,
    LoginView, LogoutView, ForgotPasswordView, PasswordResetSentView,
    CustomPasswordResetConfirmView, SelectAccountTypeView, UserSearchApiView
)

app_name = 'accounts'

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('verify-email/pending/', VerifyEmailPendingView.as_view(), name='verify_email_pending'),
    path('verify-email/resend/', ResendVerificationView.as_view(), name='resend_verification'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('password-reset/sent/', PasswordResetSentView.as_view(), name='password_reset_sent'),
    path('password-reset-confirm/<str:uidb64>/<str:token>/', CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('select-account-type/', SelectAccountTypeView.as_view(), name='select_account_type'),
    path('api/search/users/', UserSearchApiView.as_view(), name='user_search_api'),
]
