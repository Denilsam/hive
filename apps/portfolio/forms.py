from django import forms
from django.core.exceptions import ValidationError

from .models import Project, ProjectComment
from apps.profiles.models import Skill


from apps.common.file_validation import validate_uploaded_image

class ProjectForm(forms.ModelForm):
    tech_tags = forms.CharField(
        max_length=255,
        required=True,
        label="Technologies (comma-separated)",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': 'e.g. Django, React, PostgreSQL, Tailwind CSS'
        })
    )

    class Meta:
        model = Project
        fields = [
            'title', 'category', 'short_description', 'description',
            'project_image', 'github_url', 'demo_url', 'video_url',
            'is_featured', 'visibility'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
                'placeholder': 'e.g. MarketHub'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800'
            }),
            'short_description': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
                'placeholder': 'e.g. Multi-vendor marketplace built with Django and React'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
                'placeholder': 'Detailed explanation of the project features, system architecture, and installation guides...',
                'rows': 6
            }),
            'github_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
                'placeholder': 'https://github.com/username/project'
            }),
            'demo_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
                'placeholder': 'https://demo.project.com'
            }),
            'video_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
                'placeholder': 'https://youtube.com/watch?v=demo'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800',
                'type': 'date'
            }),
            'is_featured': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 bg-white/50'
            }),
            'visibility': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800'
            }),
            'project_image': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800'
            }),
        }

    def clean_project_image(self):
        img = self.cleaned_data.get('project_image')
        if img:
            validate_uploaded_image(img)
        return img

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Populate tech_tags with current project skills
            self.fields['tech_tags'].initial = ", ".join(
                self.instance.technologies.values_list('name', flat=True)
            )

    def save(self, commit=True):
        project = super().save(commit=False)
        
        def save_m2m_custom():
            # Run original save_m2m if any
            if hasattr(self, '_save_m2m'):
                self._save_m2m()
            
            # Save comma-separated technologies (normalize title case)
            tech_tags = self.cleaned_data.get('tech_tags', '')
            skills = [t.strip().title() for t in tech_tags.split(',') if t.strip()]
            
            # Clear and re-add ManyToMany mappings
            project.technologies.clear()
            for name in skills:
                skill, created = Skill.objects.get_or_create(name=name)
                project.technologies.add(skill)

        if commit:
            project.save()
            save_m2m_custom()
        else:
            self.save_m2m = save_m2m_custom
            
        return project


class ProjectCommentForm(forms.ModelForm):
    class Meta:
        model = ProjectComment
        fields = ['content']
        widgets = {
            'content': forms.TextInput(attrs={
                'class': 'w-full pl-4 pr-12 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all text-sm',
                'placeholder': 'Write a response...',
                'autocomplete': 'off'
            })
        }


from .models import Certificate

class CertificateForm(forms.ModelForm):
    class Meta:
        model = Certificate
        fields = ['title', 'organization', 'issue_date', 'certificate_url', 'certificate_file']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
                'placeholder': 'e.g. AWS Certified Solutions Architect'
            }),
            'organization': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
                'placeholder': 'e.g. Amazon Web Services (AWS)'
            }),
            'issue_date': forms.DateInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800',
                'type': 'date'
            }),
            'certificate_url': forms.URLInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
                'placeholder': 'https://credentials.com/verify/123'
            }),
            'certificate_file': forms.FileInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800'
            }),
        }
