def notifications_context(request):
    if request.user.is_authenticated:
        # Fetch unread count
        unread_count = request.user.notifications.filter(is_read=False).count()
        # Fetch up to 5 latest notifications (unread first or just latest)
        latest_notifs = request.user.notifications.order_by('-created_at')[:5]
        return {
            'unread_notifications_count': unread_count,
            'latest_notifications': latest_notifs
        }
    return {
        'unread_notifications_count': 0,
        'latest_notifications': []
    }
