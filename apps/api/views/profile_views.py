from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from apps.profiles.models import Profile
from apps.api.serializers import ProfileSerializer

User = get_user_model()


class MyProfileView(APIView):
    """
    GET /api/v1/profiles/me/
    PATCH /api/v1/profiles/me/
    Fetch or update authenticated user profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, *args, **kwargs):
        profile, _ = Profile.objects.get_or_create(user=request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True, context={'request': request})
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserProfileDetailView(APIView):
    """
    GET /api/v1/profiles/<user_id>/
    Fetch public profile for a specific user ID.
    Allows unauthenticated access for public profile viewing matching website behavior.
    """
    permission_classes = [AllowAny]

    def get(self, request, user_id, *args, **kwargs):
        target_user = get_object_or_404(User, id=user_id)
        profile, _ = Profile.objects.get_or_create(user=target_user)
        serializer = ProfileSerializer(profile, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
