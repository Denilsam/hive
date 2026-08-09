from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect, render

# Root URL redirect based on authentication
def home_view(request):
    if request.user.is_authenticated:
        return redirect('posts:feed')
    return redirect('accounts:login')

urlpatterns = [
    path('admin/', admin.site.urls),
    # Accounts local routing
    path('', include('apps.accounts.urls')),
    # Profiles local routing
    path('', include('apps.profiles.urls')),
    # Posts local routing
    path('', include('apps.posts.urls')),
    # Portfolio local routing
    path('', include('apps.portfolio.urls')),
    # Connections local routing
    path('', include('apps.connections.urls')),

    # Marketplace local routing
    path('', include('apps.marketplace.urls')),
    # Chat local routing
    path('', include('apps.chat.urls')),
    # Notifications local routing
    path('', include('apps.notifications.urls')),
    # django-allauth social / Google authentication paths
    path('accounts/', include('allauth.urls')),
    # Future REST API endpoints
    path('api/', include('apps.api.urls')),
    # Custom Admin Dashboard routing
    path('hive-admin/', include('apps.admin_dashboard.urls')),
    path('connect-admin/<path:subpath>', lambda req, subpath: redirect(f'/hive-admin/{subpath}', permanent=True)),
    path('connect-admin/', lambda req: redirect('/hive-admin/', permanent=True)),
    # Main home landing page
    path('', home_view, name='home'),
]

# Static and media routing for development server
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
