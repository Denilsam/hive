from .base import *
import dj_database_url

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-dev-connect-secret-key-12345')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Email OTP Verification (Default True; can be disabled via ENABLE_EMAIL_OTP=false)
ENABLE_EMAIL_OTP = os.getenv('ENABLE_EMAIL_OTP', 'True').strip().lower() in ('true', '1', 'yes', 't')

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,*').split(',')

# PostgreSQL as primary development database (No SQLite fallback)
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("The DATABASE_URL environment variable must be set in development.")

DATABASES = {
    'default': dj_database_url.config(
        default=DATABASE_URL,
        conn_max_age=600,
    )
}

# Email configurations for development (e.g. Mailtrap)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.mailtrap.io')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 2525))
EMAIL_HOST_USER = os.getenv('EMAIL_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
EMAIL_USE_TLS = True

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
else:
    # Console email backend fallback if no SMTP credentials exist in environment
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Cache configuration (Local memory cache for dev)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}
