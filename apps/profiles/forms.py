from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import Profile, Education, Experience, UserSkill, Certificate, Skill

User = get_user_model()


from apps.common.file_validation import validate_uploaded_image

class ProfileForm(forms.ModelForm):
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
    headline = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': 'Python Developer | Django | AI Enthusiast'
        })
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': 'Tell us about your professional background...',
            'rows': 4
        })
    )
    location = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': 'San Francisco, CA'
        })
    )
    website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': 'https://yourwebsite.com'
        })
    )
    github_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': 'https://github.com/username'
        })
    )
    linkedin_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': 'https://linkedin.com/in/username'
        })
    )
    twitter_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': 'https://twitter.com/username'
        })
    )
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': '+1 (555) 123-4567'
        })
    )
    profile_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'hidden',
            'id': 'profile-image-upload',
            'accept': 'image/*'
        })
    )
    cover_image = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'hidden',
            'id': 'cover-image-upload',
            'accept': 'image/*'
        })
    )

    class Meta:
        model = Profile
        fields = [
            'headline', 'bio', 'location', 'website',
            'github_url', 'linkedin_url', 'twitter_url', 'phone_number',
            'profile_image', 'cover_image'
        ]

    def clean_profile_image(self):
        img = self.cleaned_data.get('profile_image')
        if img:
            validate_uploaded_image(img)
        return img

    def clean_cover_image(self):
        img = self.cleaned_data.get('cover_image')
        if img:
            validate_uploaded_image(img)
        return img

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        if commit:
            profile.save()
        return profile


class EducationForm(forms.ModelForm):
    class Meta:
        model = Education
        fields = ['degree', 'institution', 'field_of_study', 'start_year', 'end_year', 'description']
        widgets = {
            'degree': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800', 'placeholder': 'e.g. BCA, BTech'}),
            'institution': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800', 'placeholder': 'e.g. Stanford University'}),
            'field_of_study': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800', 'placeholder': 'e.g. Computer Science'}),
            'start_year': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800', 'placeholder': 'e.g. 2021'}),
            'end_year': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800', 'placeholder': 'e.g. 2024 (leave blank if ongoing)'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800', 'rows': 3, 'placeholder': 'Describe your coursework, projects, or honors...'}),
        }


class ExperienceForm(forms.ModelForm):
    start_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800', 'type': 'date'}),
        input_formats=['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']
    )
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800', 'type': 'date'}),
        input_formats=['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']
    )

    class Meta:
        model = Experience
        fields = ['company_name', 'role', 'employment_type', 'start_date', 'end_date', 'currently_working', 'description']
        widgets = {
            'company_name': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800', 'placeholder': 'e.g. Google'}),
            'role': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800', 'placeholder': 'e.g. Software Engineer'}),
            'employment_type': forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800'}),
            'currently_working': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 bg-white/50'}),
            'description': forms.Textarea(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800', 'rows': 3, 'placeholder': 'Describe your roles and achievements...'}),
        }


class UserSkillForm(forms.Form):
    skill_name = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': 'e.g. Python, Django, Tailwind CSS'
        })
    )
    level = forms.ChoiceField(
        choices=UserSkill.SkillLevel.choices,
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800'
        })
    )

    def clean_skill_name(self):
        return self.cleaned_data.get('skill_name').strip()


class CertificateForm(forms.ModelForm):
    issue_date = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800', 'type': 'date'}),
        input_formats=['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d']
    )

    class Meta:
        model = Certificate
        fields = ['title', 'organization', 'issue_date', 'certificate_url', 'certificate_file']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800', 'placeholder': 'e.g. AWS Certified Solutions Architect'}),
            'organization': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800', 'placeholder': 'e.g. Amazon Web Services'}),
            'certificate_url': forms.URLInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800', 'placeholder': 'e.g. https://aws.amazon.com/verification'}),
            'certificate_file': forms.FileInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800'}),
        }
