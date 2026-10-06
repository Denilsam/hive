from django.urls import path
from . import views

app_name = 'api'

urlpatterns = [
    path('', views.api_root, name='root'),
    path('v1/auth/register/', views.MobileRegisterView.as_view(), name='auth_register'),
    path('v1/auth/token/', views.MobileTokenObtainPairView.as_view(), name='auth_token_obtain'),
    path('v1/auth/token/refresh/', views.TokenRefreshView.as_view(), name='auth_token_refresh'),
    path('v1/auth/me/', views.CurrentUserView.as_view(), name='auth_me'),
    path('v1/auth/otp/verify/', views.MobileOTPVerifyView.as_view(), name='auth_otp_verify'),
]
