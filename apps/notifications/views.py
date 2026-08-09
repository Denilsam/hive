from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponseForbidden

from .models import Notification
from .services import mark_notification_read, mark_all_read


class NotificationListView(LoginRequiredMixin, View):
    template_name = 'notifications/notification_list.html'

    def get(self, request):
        queryset = Notification.objects.filter(receiver=request.user).select_related('sender', 'sender__profile')

        # Pagination (15 notifications per page)
        paginator = Paginator(queryset, 15)
        page_number = request.GET.get('page')
        notifications_page = paginator.get_page(page_number)

        # Build following_ids relative to request.user (viewer) for follow notifications
        sender_ids = [n.sender_id for n in notifications_page if n.sender_id]
        from apps.connections.models import Follow
        following_ids = set(
            Follow.objects.filter(follower=request.user, following_id__in=sender_ids).values_list('following_id', flat=True)
        )

        for notif in notifications_page:
            if notif.sender_id:
                notif.is_following_actor = (notif.sender_id in following_ids)

        return render(request, self.template_name, {
            'notifications': notifications_page,
            'following_ids': following_ids
        })


class NotificationReadView(LoginRequiredMixin, View):
    def post(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        if notification.receiver != request.user:
            return HttpResponseForbidden("You do not have permission to modify this notification.")

        mark_notification_read(pk, request.user)
        
        # Redirect to related_url if provided, else to list
        if notification.related_url:
            return redirect(notification.related_url)
        return redirect('notifications:notification_list')

    # Also support GET request for simple clicking transition links
    def get(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        if notification.receiver != request.user:
            return HttpResponseForbidden("You do not have permission to modify this notification.")

        mark_notification_read(pk, request.user)
        
        if notification.related_url:
            return redirect(notification.related_url)
        return redirect('notifications:notification_list')


class MarkAllReadView(LoginRequiredMixin, View):
    def post(self, request):
        mark_all_read(request.user)
        messages.success(request, "All notifications marked as read.")
        return redirect('notifications:notification_list')

    # Also support GET
    def get(self, request):
        mark_all_read(request.user)
        messages.success(request, "All notifications marked as read.")
        return redirect('notifications:notification_list')
