from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic.edit import FormView
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.mixins import LoginRequiredMixin

from .forms import (
    RegisterForm, LoginForm, ForgotPasswordForm,
    ResetPasswordConfirmForm, SelectAccountTypeForm
)
from .tokens import email_verification_token

User = get_user_model()


from .models import EmailOTP

def mask_email(email):
    if not email or '@' not in email:
        return email
    name, domain = email.split('@', 1)
    if len(name) <= 2:
        masked_name = name[0] + "*"
    else:
        masked_name = name[0] + "*" * (len(name) - 2) + name[-1]
    return f"{masked_name}@{domain}"


def send_verification_otp(request, user):
    """
    Generates a 6-digit numeric OTP, hashes and stores it, and sends the raw OTP via email.
    Enforces a 60-second cooldown on sending.
    """
    last_otp = EmailOTP.objects.filter(user=user).first()
    if last_otp and (timezone.now() - last_otp.created_at).total_seconds() < 60:
        remaining = int(60 - (timezone.now() - last_otp.created_at).total_seconds())
        return False, f"Please wait {remaining} seconds before requesting a new code."

    raw_otp, otp_obj = EmailOTP.generate_otp_for_user(user)

    subject = "Verify your Hive account"
    message = (
        f"Welcome to Hive!\n\n"
        f"Your verification code is: {raw_otp}\n\n"
        f"This code expires in 10 minutes.\n\n"
        f"If you did not create a Hive account, you can ignore this email."
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    return True, "A 6-digit verification code has been sent to your email."


class RegisterView(FormView):
    template_name = 'accounts/register.html'
    form_class = RegisterForm

    def get_success_url(self):
        if getattr(settings, 'ENABLE_EMAIL_OTP', True):
            return reverse_lazy('accounts:verify_email_pending')
        return reverse_lazy('accounts:login')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import AuthLandingImage
        context['showcase_images'] = AuthLandingImage.objects.filter(is_active=True)
        return context

    def form_valid(self, form):
        user = form.save()
        if getattr(settings, 'ENABLE_EMAIL_OTP', True):
            success, msg = send_verification_otp(self.request, user)
            self.request.session['unverified_user_email'] = user.email
            return redirect('accounts:verify_email_pending')
        else:
            messages.success(self.request, "Account created successfully! You can now log in.")
            return redirect('accounts:login')


class VerifyEmailPendingView(View):
    """
    Renders OTP verification page where user submits 6-digit OTP code.
    """
    def get(self, request):
        if not getattr(settings, 'ENABLE_EMAIL_OTP', True):
            messages.info(request, "Email verification is currently disabled. You can log in directly.")
            return redirect('accounts:login')

        email = request.session.get('unverified_user_email')
        if not email:
            messages.error(request, "Please sign up or log in to verify your email.")
            return redirect('accounts:register')

        try:
            user = User.objects.get(email=email)
            if user.is_verified:
                messages.info(request, "Your email is already verified. Please log in.")
                return redirect('accounts:login')
        except User.DoesNotExist:
            return redirect('accounts:register')

        last_otp = EmailOTP.objects.filter(user=user).first()
        cooldown_remaining = 0
        if last_otp:
            elapsed = (timezone.now() - last_otp.created_at).total_seconds()
            if elapsed < 60:
                cooldown_remaining = int(60 - elapsed)

        return render(request, 'accounts/verify_email_pending.html', {
            'email': email,
            'masked_email': mask_email(email),
            'cooldown_remaining': cooldown_remaining
        })

    def post(self, request):
        if not getattr(settings, 'ENABLE_EMAIL_OTP', True):
            messages.info(request, "Email verification is currently disabled. You can log in directly.")
            return redirect('accounts:login')

        email = request.session.get('unverified_user_email') or request.POST.get('email', '').strip().lower()
        if not email:
            messages.error(request, "Session expired. Please log in to request a verification code.")
            return redirect('accounts:login')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, "Account not found.")
            return redirect('accounts:register')

        if user.is_verified:
            messages.info(request, "Account is already verified. Please log in.")
            return redirect('accounts:login')

        # Read 6-digit OTP input from single input or multiple digit inputs
        otp_digits = request.POST.getlist('otp_digit')
        if otp_digits and len(otp_digits) == 6:
            input_otp = "".join(otp_digits).strip()
        else:
            input_otp = request.POST.get('otp', '').strip()

        if not input_otp or len(input_otp) != 6 or not input_otp.isdigit():
            messages.error(request, "Please enter a valid 6-digit numeric verification code.")
            return redirect('accounts:verify_email_pending')

        active_otp = EmailOTP.objects.filter(user=user, is_used=False).first()
        if not active_otp:
            messages.error(request, "No active verification code found. Please request a new code.")
            return redirect('accounts:verify_email_pending')

        is_valid, reason = active_otp.verify_otp(input_otp)

        if is_valid:
            user.is_verified = True
            user.is_active = True
            user.save()

            if 'unverified_user_email' in request.session:
                del request.session['unverified_user_email']

            messages.success(request, "Email verified successfully! You can now log in.")
            return redirect('accounts:login')
        else:
            if reason == "TOO_MANY_ATTEMPTS":
                messages.error(request, "Too many incorrect attempts. Please request a new verification code.")
            elif reason == "EXPIRED_OR_LIMITED":
                messages.error(request, "This verification code has expired. Please request a new code.")
            else:
                messages.error(request, "Incorrect verification code.")

            return redirect('accounts:verify_email_pending')


class ResendVerificationView(View):
    def post(self, request):
        if not getattr(settings, 'ENABLE_EMAIL_OTP', True):
            messages.info(request, "Email verification is currently disabled.")
            return redirect('accounts:login')

        email = request.session.get('unverified_user_email') or request.POST.get('email', '').strip().lower()
        if not email:
            messages.error(request, "Session expired. Please log in to verify your email.")
            return redirect('accounts:login')

        try:
            user = User.objects.get(email=email)
            if user.is_verified:
                messages.info(request, "This account is already verified. Please log in.")
                return redirect('accounts:login')

            success, msg = send_verification_otp(request, user)
            if success:
                messages.success(request, msg)
            else:
                messages.error(request, msg)
            
            request.session['unverified_user_email'] = email
        except User.DoesNotExist:
            messages.error(request, "No account associated with this email.")

        return redirect('accounts:verify_email_pending')


class LoginView(FormView):
    template_name = 'accounts/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import AuthLandingImage
        context['showcase_images'] = AuthLandingImage.objects.filter(is_active=True)
        return context

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        email = form.cleaned_data.get('email').lower()
        password = form.cleaned_data.get('password')
        
        user = authenticate(self.request, username=email, password=password)
        
        if user is not None:
            if not user.is_active and user.is_verified:
                messages.error(self.request, "Your account has been deactivated. Please contact support.")
                return self.form_invalid(form)

            if not user.is_verified:
                if getattr(settings, 'ENABLE_EMAIL_OTP', True):
                    self.request.session['unverified_user_email'] = email
                    send_verification_otp(self.request, user)
                    messages.error(self.request, "Please verify your email with the 6-digit code before continuing.")
                    return redirect('accounts:verify_email_pending')
                else:
                    user.is_verified = True
                    user.is_active = True
                    user.save(update_fields=['is_verified', 'is_active'])

            login(self.request, user)
            messages.success(self.request, f"Welcome back, {user.first_name}!")
            
            # Check if account type is set
            if not user.account_type:
                return redirect('accounts:select_account_type')
            
            # Redirect to next parameter if present and safe, otherwise default to home
            next_url = self.request.GET.get('next') or self.request.POST.get('next')
            if next_url and next_url.startswith('/'):
                return redirect(next_url)
            
            return redirect('home')
        else:
            messages.error(self.request, "Invalid email or password.")
            return self.form_invalid(form)


class LogoutView(View):
    """
    Secure POST logout view.
    """
    def post(self, request):
        if request.user.is_authenticated:
            logout(request)
            messages.success(request, "You have been successfully logged out.")
        return redirect('home')


class ForgotPasswordView(FormView):
    template_name = 'accounts/forgot_password.html'
    form_class = ForgotPasswordForm
    success_url = reverse_lazy('accounts:password_reset_sent')

    def form_valid(self, form):
        email = form.cleaned_data.get('email', '').strip().lower()
        user = User.objects.filter(email__iexact=email, is_active=True).first()
        
        if user:
            # Generate password reset token
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_path = reverse('accounts:password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            reset_url = self.request.build_absolute_uri(reset_path)
            
            subject = "Reset your Hive password"
            message = (
                f"Hi {user.first_name},\n\n"
                f"You requested to reset your password. Please click the link below to set a new password:\n"
                f"{reset_url}\n\n"
                f"If you did not request this, you can safely ignore this email.\n\n"
                f"Hive team."
            )
            
            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            except Exception:
                pass
        return super().form_valid(form)


class PasswordResetSentView(View):
    def get(self, request):
        return render(request, 'accounts/password_reset_sent.html')


class CustomPasswordResetConfirmView(FormView):
    template_name = 'accounts/password_reset_confirm.html'
    form_class = ResetPasswordConfirmForm
    success_url = reverse_lazy('accounts:login')

    def dispatch(self, request, uidb64, token, *args, **kwargs):
        self.uidb64 = uidb64
        self.token = token
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            self.user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            self.user = None

        if self.user is not None and default_token_generator.check_token(self.user, token):
            return super().dispatch(request, *args, **kwargs)
        else:
            messages.error(request, "The password reset link is invalid or has expired.")
            return render(request, 'accounts/password_reset_failed.html')

    def form_valid(self, form):
        self.user.set_password(form.cleaned_data['password'])
        self.user.save()
        messages.success(self.request, "Your password has been successfully reset! You can now log in.")
        return super().form_valid(form)


class SelectAccountTypeView(LoginRequiredMixin, FormView):
    template_name = 'accounts/select_account_type.html'
    form_class = SelectAccountTypeForm
    success_url = reverse_lazy('home')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Account type successfully selected.")
        return super().form_valid(form)


from django.http import JsonResponse
from django.db.models import Q

import re

class UserSearchApiView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        if not query or len(query) < 1:
            return JsonResponse({'results': []})
        
        # Escape special characters
        safe_query = re.sub(r'[^\w\s-]', '', query)
        if not safe_query:
            return JsonResponse({'results': []})

        users = User.objects.filter(
            Q(first_name__icontains=safe_query) |
            Q(last_name__icontains=safe_query) |
            Q(username__icontains=safe_query)
        ).filter(is_superuser=False, is_active=True).exclude(id=request.user.id).select_related('profile')[:5]
        
        results = []
        for user in users:
            avatar = user.profile.profile_image.url if (hasattr(user, 'profile') and user.profile.profile_image) else ""
            headline = user.profile.headline if hasattr(user, 'profile') and user.profile.headline else "Hive Member"
            results.append({
                'id': user.id,
                'username': user.username,
                'full_name': f"{user.first_name} {user.last_name}".strip() or user.username,
                'headline': headline,
                'avatar': avatar,
                'url': reverse('profiles:profile_detail', kwargs={'username': user.username})
            })
            
        return JsonResponse({'results': results})

