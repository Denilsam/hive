from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Q
from apps.connections.models import Follow, ConnectionRequest, Connection
from apps.api.serializers import (
    UserSerializer,
    FollowSerializer,
    ConnectionRequestSerializer,
    ConnectionSerializer,
)

User = get_user_model()


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class FollowToggleView(APIView):
    """
    POST /api/v1/connections/follow/<user_id>/
    Follow or unfollow a user.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, user_id, *args, **kwargs):
        if request.user.id == user_id:
            return Response({"detail": "You cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)

        target_user = get_object_or_404(User, id=user_id)
        follow, created = Follow.objects.get_or_create(follower=request.user, following=target_user)

        if not created:
            follow.delete()
            is_following = False
        else:
            is_following = True

        follower_count = target_user.follower_relations.count()
        return Response({
            "is_following": is_following,
            "follower_count": follower_count
        }, status=status.HTTP_200_OK)


class FollowersListView(APIView):
    """
    GET /api/v1/connections/followers/<user_id>/
    List users following a given user.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request, user_id, *args, **kwargs):
        target_user = get_object_or_404(User, id=user_id)
        followers = Follow.objects.filter(following=target_user).select_related('follower', 'follower__profile')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(followers, request)

        if page is not None:
            serializer = FollowSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = FollowSerializer(followers, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class FollowingListView(APIView):
    """
    GET /api/v1/connections/following/<user_id>/
    List users that a given user is following.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request, user_id, *args, **kwargs):
        target_user = get_object_or_404(User, id=user_id)
        following = Follow.objects.filter(follower=target_user).select_related('following', 'following__profile')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(following, request)

        if page is not None:
            serializer = FollowSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = FollowSerializer(following, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ConnectionRequestListCreateView(APIView):
    """
    GET /api/v1/connections/requests/ (Pending requests received by auth user)
    POST /api/v1/connections/request/<user_id>/ (Send connection request)
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request, *args, **kwargs):
        requests = ConnectionRequest.objects.filter(
            receiver=request.user,
            status=ConnectionRequest.Status.PENDING
        ).select_related('sender', 'sender__profile').order_by('-created_at')

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(requests, request)

        if page is not None:
            serializer = ConnectionRequestSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = ConnectionRequestSerializer(requests, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, user_id, *args, **kwargs):
        if request.user.id == user_id:
            return Response({"detail": "You cannot send a connection request to yourself."}, status=status.HTTP_400_BAD_REQUEST)

        receiver = get_object_or_404(User, id=user_id)

        # Check existing connection
        if Connection.objects.filter(
            Q(user1=request.user, user2=receiver) | Q(user1=receiver, user2=request.user)
        ).exists():
            return Response({"detail": "You are already connected to this user."}, status=status.HTTP_400_BAD_REQUEST)

        # Check pending request
        existing_req = ConnectionRequest.objects.filter(
            sender=request.user, receiver=receiver, status=ConnectionRequest.Status.PENDING
        ).first()

        if existing_req:
            return Response({"detail": "Connection request already pending."}, status=status.HTTP_400_BAD_REQUEST)

        conn_req = ConnectionRequest.objects.create(sender=request.user, receiver=receiver)
        serializer = ConnectionRequestSerializer(conn_req, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ConnectionRequestActionView(APIView):
    """
    POST /api/v1/connections/request/<id>/accept/
    POST /api/v1/connections/request/<id>/reject/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id, action, *args, **kwargs):
        conn_req = get_object_or_404(ConnectionRequest, id=id, receiver=request.user)

        if conn_req.status != ConnectionRequest.Status.PENDING:
            return Response({"detail": f"This request is already {conn_req.status.lower()}."}, status=status.HTTP_400_BAD_REQUEST)

        if action == 'accept':
            conn_req.status = ConnectionRequest.Status.ACCEPTED
            conn_req.save()
            Connection.objects.get_or_create(user1=conn_req.sender, user2=conn_req.receiver)
            message = "Connection request accepted."
        elif action == 'reject':
            conn_req.status = ConnectionRequest.Status.REJECTED
            conn_req.save()
            message = "Connection request rejected."
        else:
            return Response({"detail": "Invalid action. Use 'accept' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ConnectionRequestSerializer(conn_req, context={'request': request})
        return Response({
            "message": message,
            "request": serializer.data
        }, status=status.HTTP_200_OK)


class NetworkSummaryView(APIView):
    """
    GET /api/v1/connections/network/
    Summary of network stats for authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        followers_count = Follow.objects.filter(following=user).count()
        following_count = Follow.objects.filter(follower=user).count()
        connections_count = Connection.objects.filter(Q(user1=user) | Q(user2=user)).count()
        pending_requests_count = ConnectionRequest.objects.filter(receiver=user, status=ConnectionRequest.Status.PENDING).count()

        return Response({
            "followers_count": followers_count,
            "following_count": following_count,
            "connections_count": connections_count,
            "pending_requests_count": pending_requests_count,
        }, status=status.HTTP_200_OK)
