from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from apps.notifications.models import Notification
from apps.api.serializers import NotificationSerializer


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class NotificationListView(APIView):
    """
    GET /api/v1/notifications/
    Fetch paginated notifications for the authenticated user.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request, *args, **kwargs):
        notifications = Notification.objects.filter(receiver=request.user).select_related('sender', 'sender__profile')
        unread_count = notifications.filter(is_read=False).count()

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(notifications, request)

        if page is not None:
            serializer = NotificationSerializer(page, many=True, context={'request': request})
            response_data = paginator.get_paginated_response(serializer.data).data
            response_data['unread_count'] = unread_count
            return Response(response_data, status=status.HTTP_200_OK)

        serializer = NotificationSerializer(notifications, many=True, context={'request': request})
        return Response({
            "unread_count": unread_count,
            "results": serializer.data
        }, status=status.HTTP_200_OK)


class NotificationMarkReadView(APIView):
    """
    POST /api/v1/notifications/<id>/read/
    Mark a single notification as read.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, id, *args, **kwargs):
        notification = get_object_or_404(Notification, id=id, receiver=request.user)
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        serializer = NotificationSerializer(notification, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class NotificationReadAllView(APIView):
    """
    POST /api/v1/notifications/read-all/
    Mark all notifications for the authenticated user as read.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        updated_count = Notification.objects.filter(receiver=request.user, is_read=False).update(is_read=True)
        return Response({
            "message": f"Marked {updated_count} notifications as read.",
            "marked_read_count": updated_count
        }, status=status.HTTP_200_OK)
