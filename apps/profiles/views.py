from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Profile, Education, Experience, Skill, UserSkill, Certificate
from apps.connections.models import Follow
from django.db import models
from .forms import (
    ProfileForm, EducationForm, ExperienceForm,
    UserSkillForm, CertificateForm
)

User = get_user_model()


class ProfileDetailView(DetailView):
    model = User
    template_name = 'profiles/profile_detail.html'
    context_object_name = 'profile_user'

    def get_object(self, queryset=None):
        username = self.kwargs.get('username')
        if not username or username == 'None':
            if self.request.user.is_authenticated:
                # Fallback to current user if their profile was requested with None
                if not self.request.user.username:
                    self.request.user.save() # generate username if missing
                return self.request.user
            else:
                from django.http import Http404
                raise Http404("User profile not found.")
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            if self.request.user.is_authenticated:
                return self.request.user
            from django.http import Http404
            raise Http404("User profile not found.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        # Load profile related elements
        context['profile'] = getattr(user, 'profile', None)
        context['education_list'] = user.education_set.all().order_by('-start_year')
        context['experience_list'] = user.experience_set.all().order_by('-start_date')
        context['skills'] = user.userskill_set.all().select_related('skill')
        context['certificates'] = user.certificate_set.all().order_by('-issue_date')
        
        # Stats counts
        context['posts_count'] = user.post_set.count() if hasattr(user, 'post_set') else 0
        context['followers_count'] = Follow.objects.filter(following=user).count()
        context['following_count'] = Follow.objects.filter(follower=user).count()

        # Flag to identify if viewing own profile
        context['is_own_profile'] = (self.request.user == user)

        if self.request.user.is_authenticated and not context['is_own_profile']:
            context['is_following'] = Follow.objects.filter(follower=self.request.user, following=user).exists()

        return context


class ProfileEditView(LoginRequiredMixin, View):
    template_name = 'profiles/profile_edit.html'

    def get(self, request):
        if request.user.is_superuser:
            messages.error(request, "Superadmin accounts do not have a member profile.")
            return redirect('admin_dashboard:dashboard')

        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile_form = ProfileForm(instance=profile)
        
        # Instantiate placeholder forms for modals/adding sections
        education_form = EducationForm()
        experience_form = ExperienceForm()
        skill_form = UserSkillForm()
        certificate_form = CertificateForm()

        education_list = request.user.education_set.all().order_by('-start_year')
        experience_list = request.user.experience_set.all().order_by('-start_date')
        skills = request.user.userskill_set.all().select_related('skill')
        certificates = request.user.certificate_set.all().order_by('-issue_date')

        return render(request, self.template_name, {
            'profile_form': profile_form,
            'education_form': education_form,
            'experience_form': experience_form,
            'skill_form': skill_form,
            'certificate_form': certificate_form,
            'education_list': education_list,
            'experience_list': experience_list,
            'skills': skills,
            'certificates': certificates,
            'profile': profile
        })

    def post(self, request):
        if request.user.is_superuser:
            messages.error(request, "Superadmin accounts do not have a member profile.")
            return redirect('admin_dashboard:dashboard')

        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect('profiles:profile_detail', username=request.user.username)
        
        for field, errs in profile_form.errors.items():
            messages.error(request, f"{field.replace('_', ' ').title()}: {errs[0]}")

        # Reload with errors
        education_list = request.user.education_set.all().order_by('-start_year')
        experience_list = request.user.experience_set.all().order_by('-start_date')
        skills = request.user.userskill_set.all().select_related('skill')
        certificates = request.user.certificate_set.all().order_by('-issue_date')
        
        return render(request, self.template_name, {
            'profile_form': profile_form,
            'education_form': EducationForm(),
            'experience_form': ExperienceForm(),
            'skill_form': UserSkillForm(),
            'certificate_form': CertificateForm(),
            'education_list': education_list,
            'experience_list': experience_list,
            'skills': skills,
            'certificates': certificates,
            'profile': profile
        })


# --- Profile Sub-Model Creation & Deletion View Controllers (Secured to request.user) ---

class EducationCreateView(LoginRequiredMixin, View):
    def post(self, request):
        form = EducationForm(request.POST)
        if form.is_valid():
            education = form.save(commit=False)
            education.user = request.user
            try:
                education.full_clean()
                education.save()
                messages.success(request, "Education entry successfully added.")
            except ValidationError as ve:
                for field, errs in ve.message_dict.items():
                    messages.error(request, f"{field.replace('_', ' ').title()}: {errs[0]}")
        else:
            for field, errs in form.errors.items():
                messages.error(request, f"{field.replace('_', ' ').title()}: {errs[0]}")
        return redirect('profiles:profile_edit')


class EducationDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        education = get_object_or_404(Education, pk=pk, user=request.user)
        education.delete()
        messages.success(request, "Education entry deleted.")
        return redirect('profiles:profile_edit')


class ExperienceCreateView(LoginRequiredMixin, View):
    def post(self, request):
        form = ExperienceForm(request.POST)
        if form.is_valid():
            experience = form.save(commit=False)
            experience.user = request.user
            try:
                experience.full_clean()
                experience.save()
                messages.success(request, "Work experience entry added.")
            except ValidationError as ve:
                for field, errs in ve.message_dict.items():
                    messages.error(request, f"{field.replace('_', ' ').title()}: {errs[0]}")
        else:
            for field, errs in form.errors.items():
                messages.error(request, f"{field.replace('_', ' ').title()}: {errs[0]}")
        return redirect('profiles:profile_edit')


class ExperienceDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        experience = get_object_or_404(Experience, pk=pk, user=request.user)
        experience.delete()
        messages.success(request, "Work experience entry deleted.")
        return redirect('profiles:profile_edit')


class UserSkillCreateView(LoginRequiredMixin, View):
    def post(self, request):
        form = UserSkillForm(request.POST)
        if form.is_valid():
            skill_name = form.cleaned_data['skill_name'].lower().title()
            level = form.cleaned_data['level']
            
            # Lookup or create skill name
            skill, created = Skill.objects.get_or_create(name=skill_name)
            
            # Create user skill map (or update if already exists)
            userskill, created = UserSkill.objects.update_or_create(
                user=request.user,
                skill=skill,
                defaults={'level': level}
            )
            messages.success(request, f"Skill '{skill_name}' added/updated.")
        else:
            for field, errs in form.errors.items():
                messages.error(request, f"{field.replace('_', ' ').title()}: {errs[0]}")
        return redirect('profiles:profile_edit')


class UserSkillDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        userskill = get_object_or_404(UserSkill, pk=pk, user=request.user)
        userskill.delete()
        messages.success(request, "Skill removed from profile.")
        return redirect('profiles:profile_edit')


class CertificateCreateView(LoginRequiredMixin, View):
    def post(self, request):
        form = CertificateForm(request.POST, request.FILES)
        if form.is_valid():
            certificate = form.save(commit=False)
            certificate.user = request.user
            try:
                certificate.full_clean()
                certificate.save()
                messages.success(request, "Certificate entry successfully added.")
            except ValidationError as ve:
                for field, errs in ve.message_dict.items():
                    messages.error(request, f"{field.replace('_', ' ').title()}: {errs[0]}")
        else:
            for field, errs in form.errors.items():
                messages.error(request, f"{field.replace('_', ' ').title()}: {errs[0]}")
        return redirect('profiles:profile_edit')


class CertificateDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        certificate = get_object_or_404(Certificate, pk=pk, user=request.user)
        # Delete media file if it exists
        if certificate.certificate_file:
            certificate.certificate_file.delete(save=False)
        certificate.delete()
        messages.success(request, "Certificate entry deleted.")
        return redirect('profiles:profile_edit')
