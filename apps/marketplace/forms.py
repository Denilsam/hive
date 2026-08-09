from django import forms
from .models import Collaboration, CollaborationApplication
from apps.profiles.models import Skill


class CollaborationForm(forms.ModelForm):
    required_skills_input = forms.CharField(
        max_length=255,
        required=True,
        label="Required Skills (comma-separated)",
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
            'placeholder': 'e.g. Python, Django, UI Design, React'
        })
    )

    class Meta:
        model = Collaboration
        fields = [
            'title', 'description', 'category', 'project_type',
            'budget_type', 'budget_amount', 'duration'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
                'placeholder': 'e.g. Co-founder for EdTech platform'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
                'placeholder': 'Detailed explanation of project goals, team structure, and collaborator expectations...',
                'rows': 6
            }),
            'category': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
                'placeholder': 'e.g. Software Development, Marketing, Graphic Design'
            }),
            'project_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800'
            }),
            'budget_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800'
            }),
            'budget_amount': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
                'placeholder': 'e.g. 50,000.00 (optional if unpaid/negotiable)'
            }),
            'duration': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all',
                'placeholder': 'e.g. 3 Months, Ongoing'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            # Populate required_skills_input with current skills
            self.fields['required_skills_input'].initial = ", ".join(
                self.instance.required_skills.values_list('skill__name', flat=True)
            )

    def save(self, commit=True):
        collaboration = super().save(commit=False)
        if hasattr(self, 'user_override') and self.user_override:
            collaboration.creator = self.user_override
        
        def save_m2m_custom():
            # Save comma-separated skills
            skills_input = self.cleaned_data.get('required_skills_input', '')
            skills_list = [s.strip().title() for s in skills_input.split(',') if s.strip()]
            
            # Clear and re-add CollaborationSkill relations
            collaboration.required_skills.all().delete()
            for name in skills_list:
                skill, created = Skill.objects.get_or_create(name=name)
                from .models import CollaborationSkill
                CollaborationSkill.objects.create(collaboration=collaboration, skill=skill)

        if commit:
            collaboration.save()
            save_m2m_custom()
        else:
            self.save_m2m = save_m2m_custom
            
        return collaboration


class CollaborationApplicationForm(forms.ModelForm):
    class Meta:
        model = CollaborationApplication
        fields = ['message']
        widgets = {
            'message': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500/20 focus:border-brand-500 bg-white/50 text-slate-800 placeholder-slate-400 transition-all text-sm',
                'placeholder': 'Explain why you are a good fit for this project, and outline your relevant experience...',
                'rows': 5
            })
        }
