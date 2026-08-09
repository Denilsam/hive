from .models import PlatformSettings

def site_branding(request):
    """
    Global context processor providing centralized branding configuration
    (site_name, logo_url, favicon_url, admin_logo_url) to all templates.
    """
    try:
        settings_obj = PlatformSettings.load()
        site_name = settings_obj.site_name or 'Hive'
        logo_url = settings_obj.logo_url
        favicon_url = settings_obj.favicon_url
        admin_logo_url = settings_obj.admin_logo_url
        is_custom_logo = bool(settings_obj.logo)
        is_custom_favicon = bool(settings_obj.favicon)
        is_custom_admin_logo = bool(settings_obj.admin_logo)
        updated_at_timestamp = settings_obj.updated_at_timestamp
    except Exception:
        settings_obj = None
        site_name = 'Hive'
        logo_url = '/static/images/branding/hive_icon.svg'
        favicon_url = '/static/favicon.svg'
        admin_logo_url = '/static/images/branding/hive_icon.svg'
        is_custom_logo = False
        is_custom_favicon = False
        is_custom_admin_logo = False
        updated_at_timestamp = 1

    return {
        'site_branding': {
            'site_name': site_name,
            'logo_url': logo_url,
            'favicon_url': favicon_url,
            'admin_logo_url': admin_logo_url,
            'is_custom_logo': is_custom_logo,
            'is_custom_favicon': is_custom_favicon,
            'is_custom_admin_logo': is_custom_admin_logo,
            'updated_at_timestamp': updated_at_timestamp,
            'settings_obj': settings_obj,
        }
    }
