import os

apps_dir = "c:/Users/denil/Desktop/connect/apps"
os.makedirs(apps_dir, exist_ok=True)

# create apps/__init__.py
with open(os.path.join(apps_dir, "__init__.py"), "w") as f:
    f.write("# Connect local apps package\n")

apps = [
    "common",
    "accounts",
    "profiles",
    "posts",
    "portfolio",
    "communities",
    "marketplace",
    "opportunities",
    "chat",
    "notifications",
    "api"
]

for app in apps:
    app_path = os.path.join(apps_dir, app)
    os.makedirs(app_path, exist_ok=True)
    
    # 1. __init__.py
    with open(os.path.join(app_path, "__init__.py"), "w") as f:
        f.write(f"# App: {app}\n")
        
    # 2. apps.py
    # We capitalize the app name correctly for class definitions.
    # Note: capitalize() works fine for simple names, but let's make sure
    # we use title() or a custom mapper if needed. Since our names are simple (chat, notifications, accounts), capitalize() is perfect.
    with open(os.path.join(app_path, "apps.py"), "w") as f:
        f.write(f"""from django.apps import AppConfig


class {app.capitalize()}Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.{app}'
""")

    # 3. models.py
    if app == "common":
        with open(os.path.join(app_path, "models.py"), "w") as f:
            f.write("""from django.db import models


class TimeStampedModel(models.Model):
    \"\"\"
    An abstract base class model that provides self-updating
    'created_at' and 'updated_at' fields.
    \"\"\"
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
""")
    elif app == "accounts":
        with open(os.path.join(app_path, "models.py"), "w") as f:
            f.write("""from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    class AccountType(models.TextChoices):
        STUDENT = 'STUDENT', 'Student'
        CREATOR = 'CREATOR', 'Creator'
        FREELANCER = 'FREELANCER', 'Freelancer'
        ORGANIZATION = 'ORGANIZATION', 'Organization'
        ADMIN = 'ADMIN', 'Admin'

    account_type = models.CharField(
        max_length=20,
        choices=AccountType.choices,
        default=AccountType.STUDENT,
    )
    is_verified = models.BooleanField(default=False)
    profile_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.get_account_type_display()})"
""")
    else:
        with open(os.path.join(app_path, "models.py"), "w") as f:
            f.write(f"""from django.db import models

# Create your models here.
""")

    # 4. admin.py
    if app == "accounts":
        with open(os.path.join(app_path, "admin.py"), "w") as f:
            f.write("""from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'account_type', 'is_verified', 'profile_completed', 'is_staff')
    list_filter = ('account_type', 'is_verified', 'profile_completed', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('Custom Fields', {
            'fields': ('account_type', 'is_verified', 'profile_completed'),
        }),
    )
""")
    else:
        with open(os.path.join(app_path, "admin.py"), "w") as f:
            f.write("""from django.contrib import admin

# Register your models here.
""")

    # 5. views.py
    with open(os.path.join(app_path, "views.py"), "w") as f:
        f.write("""from django.shortcuts import render

# Create your views here.
""")

    # 6. urls.py
    if app == "api":
        with open(os.path.join(app_path, "urls.py"), "w") as f:
            f.write("""from django.urls import path
from django.http import JsonResponse

app_name = 'api'


def api_root(request):
    return JsonResponse({
        "name": "Connect API",
        "version": "1.0.0",
        "description": "Connect skills. Create opportunities."
    })


urlpatterns = [
    path('', api_root, name='root'),
]
""")
    else:
        with open(os.path.join(app_path, "urls.py"), "w") as f:
            f.write(f"""from django.urls import path

app_name = '{app}'

urlpatterns = [
    # App-specific routes
]
""")

    # 7. tests.py
    if app == "accounts":
        with open(os.path.join(app_path, "tests.py"), "w") as f:
            f.write("""from django.test import TestCase
from django.contrib.auth import get_user_model


class CustomUserModelTest(TestCase):
    def test_create_user_with_default_fields(self):
        User = get_user_model()
        user = User.objects.create_user(username='testuser', email='test@example.com', password='password123')
        
        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.account_type, User.AccountType.STUDENT)
        self.assertFalse(user.is_verified)
        self.assertFalse(user.profile_completed)
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)
        self.assertEqual(str(user), "testuser (Student)")
""")
    else:
        with open(os.path.join(app_path, "tests.py"), "w") as f:
            f.write(f"""from django.test import TestCase

# Create your tests here.
class PlaceholderTest(TestCase):
    def test_placeholder(self):
        self.assertTrue(True)
""")

# 8. Create global tests directory structure
tests_dir = "c:/Users/denil/Desktop/connect/tests"
os.makedirs(os.path.join(tests_dir, "integration"), exist_ok=True)
os.makedirs(os.path.join(tests_dir, "unit"), exist_ok=True)

with open(os.path.join(tests_dir, "__init__.py"), "w") as f:
    f.write("# Global tests package\n")

with open(os.path.join(tests_dir, "integration", "__init__.py"), "w") as f:
    f.write("# Integration tests package\n")

with open(os.path.join(tests_dir, "unit", "__init__.py"), "w") as f:
    f.write("# Unit tests package\n")

print("Successfully generated all apps boilerplate and global test directories!")
