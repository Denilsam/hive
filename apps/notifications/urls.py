from django.urls import path
from .views import NotificationListView, NotificationReadView, MarkAllReadView

app_name = 'notifications'

urlpatterns = [
    path('notifications/', NotificationListView.as_view(), name='notification_list'),
    path('notifications/read/<int:pk>/', NotificationReadView.as_view(), name='notification_read'),
    path('notifications/read-all/', MarkAllReadView.as_view(), name='mark_all_read'),
]
