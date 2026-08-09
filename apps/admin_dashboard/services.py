from .models import AdminActivityLog

def log_admin_activity(request, action, target=""):
    user = request.user if request and request.user.is_authenticated else None
    ip_address = None
    user_agent = ""
    
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    AdminActivityLog.objects.create(
        admin=user,
        action=action,
        target=str(target)[:255],
        ip_address=ip_address,
        user_agent=user_agent
    )
