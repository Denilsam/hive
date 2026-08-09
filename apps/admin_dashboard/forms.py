import os
from PIL import Image
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import AdminProfile, AdminPermission, PlatformSettings

User = get_user_model()

ALLOWED_IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp']
ALLOWED_FAVICON_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.webp', '.ico', '.svg']
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB


from apps.common.file_validation import validate_uploaded_image

def validate_image_file(file, allowed_extensions=ALLOWED_IMAGE_EXTENSIONS):
    if not file:
        return file
    validate_uploaded_image(file)
    return file


class AdminCreateForm(forms.ModelForm):
    role = forms.ChoiceField(choices=[
        (AdminProfile.Role.ADMIN_ASSISTANT, 'Admin Assistant'),
        (AdminProfile.Role.CONTENT_MODERATOR, 'Content Moderator'),
        (AdminProfile.Role.SUPPORT_ADMIN, 'Support Admin'),
    ])
    permissions = forms.ModelMultipleChoiceField(
        queryset=AdminPermission.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = AdminProfile
        fields = ['role', 'is_active']


class PlatformSettingsForm(forms.ModelForm):
    class Meta:
        model = PlatformSettings
        fields = [
            'site_name', 'logo', 'favicon', 'admin_logo',
            'maintenance_mode', 'contact_email',
            'registration_enabled', 'default_profile_visibility'
        ]
        widgets = {
            'site_name': forms.TextInput(attrs={'class': 'form-input'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-input'}),
            'default_profile_visibility': forms.TextInput(attrs={'class': 'form-input'}),
        }

    def clean_logo(self):
        logo = self.cleaned_data.get('logo')
        return validate_image_file(logo, ALLOWED_IMAGE_EXTENSIONS)

    def clean_favicon(self):
        favicon = self.cleaned_data.get('favicon')
        return validate_image_file(favicon, ALLOWED_FAVICON_EXTENSIONS)

    def clean_admin_logo(self):
        admin_logo = self.cleaned_data.get('admin_logo')
        return validate_image_file(admin_logo, ALLOWED_IMAGE_EXTENSIONS)

