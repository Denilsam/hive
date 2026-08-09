from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()


class RegisterForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': 'John'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': 'Doe'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': 'john.doe@example.com'
        })
    )
    account_type = forms.ChoiceField(
        choices=[
            ('STUDENT', 'Student'),
            ('CREATOR', 'Creator'),
            ('FREELANCER', 'Freelancer'),
            ('ORGANIZATION', 'Organization')
        ],
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 transition-all'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': '••••••••'
        }),
        validators=[validate_password]
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': '••••••••'
        })
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'account_type']

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        # Set user inactive until email is verified
        user.is_active = False
        user.is_verified = False
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
        'placeholder': 'your.email@example.com'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
        'placeholder': '••••••••'
    }))


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={
        'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
        'placeholder': 'your.email@example.com'
    }))

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        try:
            user = User.objects.get(email=email)
            if not user.is_verified:
                raise ValidationError("Your account is not verified yet. Please verify your email first.")
        except User.DoesNotExist:
            raise ValidationError("No verified account found with this email address.")
        return email


class ResetPasswordConfirmForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': '••••••••'
        }),
        validators=[validate_password]
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': '••••••••'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data


class SelectAccountTypeForm(forms.ModelForm):
    account_type = forms.ChoiceField(
        choices=[
            ('STUDENT', 'Student'),
            ('CREATOR', 'Creator'),
            ('FREELANCER', 'Freelancer'),
            ('ORGANIZATION', 'Organization')
        ],
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 transition-all'
        })
    )

    class Meta:
        model = User
        fields = ['account_type']
