from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.conf import settings
from apps.accounts.views import send_verification_otp

from apps.api.serializers import (
    UserSerializer,
    MobileRegisterSerializer,
    MobileLoginSerializer,
    MobileOTPVerifySerializer,
)


def api_root(request):
    from django.http import JsonResponse
    return JsonResponse({
        "name": "Hive REST API",
        "version": "1.0.0",
        "description": "Hive Mobile & Web API Gateway"
    })


class MobileRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = MobileRegisterSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()

        enable_otp = getattr(settings, 'ENABLE_EMAIL_OTP', False)
        if enable_otp:
            send_verification_otp(request, user)
            return Response({
                "message": "Account created successfully. A 6-digit verification code has been sent to your email.",
                "requires_otp": True,
                "email": user.email
            }, status=status.HTTP_201_CREATED)

        refresh = RefreshToken.for_user(user)
        return Response({
            "message": "Account created successfully.",
            "requires_otp": False,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)


class MobileTokenObtainPairView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = MobileLoginSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user, context={'request': request}).data
        }, status=status.HTTP_200_OK)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class MobileOTPVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = MobileOTPVerifySerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Email verified successfully.",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": UserSerializer(user, context={'request': request}).data
        }, status=status.HTTP_200_OK)
