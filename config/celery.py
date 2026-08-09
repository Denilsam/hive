import os
from celery import Celery

# Set default settings module for Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('connect')

# Load settings using CELERY_ prefix from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Automatically discover tasks.py in all registered apps
app.autodiscover_tasks()
