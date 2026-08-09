import os
from pathlib import Path
from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv

# Load environment variables at WSGI startup
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

application = get_wsgi_application()
