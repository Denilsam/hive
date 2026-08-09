from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.urls import reverse


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    """
    Custom adapter for allauth social logins.
    Automatically marks Google-authenticated users as verified
    and redirects them to select their account type if it is missing.
    """
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        if not user.username:
            base_username = user.email.split('@')[0] if user.email else "user"
            username = base_username
            counter = 1
            User = user.__class__
            while User.objects.filter(username=username).exclude(pk=user.pk).exists():
                username = f"{base_username}{counter}"
                counter += 1
            user.username = username
        # Google account emails are pre-verified
        user.is_verified = True
        user.save()
        return user

    def get_login_redirect_url(self, request):
        user = request.user
        # Redirect to account type selection if not set
        if not user.account_type:
            return reverse('accounts:select_account_type')
        return reverse('home')
