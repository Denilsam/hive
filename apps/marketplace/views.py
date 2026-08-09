from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import HttpResponseForbidden, Http404
from django.core.paginator import Paginator
from django.urls import reverse
from django.db import models
from django.core.exceptions import ValidationError

from .models import Collaboration, CollaborationSkill, CollaborationApplication
from .forms import CollaborationForm, CollaborationApplicationForm
from apps.profiles.models import Skill


class CollaborationExploreView(View):
    template_name = 'marketplace/collaboration_list.html'

    def get(self, request):
        queryset = Collaboration.objects.filter(status=Collaboration.Status.OPEN)

        # Keyword search
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                models.Q(title__icontains=q) |
                models.Q(description__icontains=q) |
                models.Q(category__icontains=q)
            )

        # Category filter
        category = request.GET.get('category', '').strip()
        if category:
            queryset = queryset.filter(category__iexact=category)

        # Budget type filter
        budget_type = request.GET.get('budget_type', '').strip()
        if budget_type:
            queryset = queryset.filter(budget_type=budget_type)

        # Skill filter
        skill_name = request.GET.get('skill', '').strip()
        if skill_name:
            queryset = queryset.filter(required_skills__skill__name__iexact=skill_name)

        # Pagination
        paginator = Paginator(queryset.distinct(), 9) # 9 cards per page
        page_number = request.GET.get('page')
        collaborations_page = paginator.get_page(page_number)

        # Unique skills list for the filter select
        available_skills = Skill.objects.filter(collaboration_skills__isnull=False).distinct()

        return render(request, self.template_name, {
            'collaborations': collaborations_page,
            'budget_types': Collaboration.BudgetType.choices,
            'project_types': Collaboration.ProjectType.choices,
            'available_skills': available_skills,
            'selected_category': category,
            'selected_budget_type': budget_type,
            'selected_skill': skill_name,
            'query': q
        })


class CollaborationDetailView(View):
    template_name = 'marketplace/collaboration_detail.html'

    def get(self, request, pk):
        collaboration = get_object_or_404(Collaboration, pk=pk)
        
        # Check if current user is owner
        is_creator = (request.user == collaboration.creator)

        # Fetch applications
        applications = None
        user_application = None
        
        if request.user.is_authenticated:
            if is_creator:
                applications = collaboration.applications.exclude(status=CollaborationApplication.Status.WITHDRAWN).select_related('applicant', 'applicant__profile')
            else:
                user_application = collaboration.applications.filter(applicant=request.user).first()

        # Skills list
        skills = collaboration.required_skills.select_related('skill').all()

        # Application Form
        application_form = CollaborationApplicationForm()

        return render(request, self.template_name, {
            'collaboration': collaboration,
            'is_creator': is_creator,
            'skills': skills,
            'applications': applications,
            'user_application': user_application,
            'application_form': application_form
        })


class CollaborationCreateView(LoginRequiredMixin, View):
    template_name = 'marketplace/publish_opportunity.html'

    def get(self, request):
        print(f"[DEBUG] Publish Opportunity GET request received | Method: {request.method}")
        form = CollaborationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        print(f"[DEBUG] Publish Opportunity POST request received | Method: {request.method} | Is POST: {request.method == 'POST'}")
        form = CollaborationForm(request.POST, request.FILES)
        if form.is_valid():
            opportunity = form.save(commit=False)
            opportunity.creator = request.user
            if hasattr(opportunity, 'user'):
                opportunity.user = request.user
            if hasattr(opportunity, 'status'):
                opportunity.status = Collaboration.Status.OPEN
            if hasattr(opportunity, 'is_active'):
                opportunity.is_active = True
            opportunity.save()
            form.save_m2m() # Saves required_skills
            print(f"[DEBUG] Opportunity saved successfully! ID: {opportunity.pk}, Title: '{opportunity.title}'")
            messages.success(request, f"Opportunity '{opportunity.title}' successfully published!")
            return redirect('marketplace:marketplace_dashboard')
        else:
            print(f"[DEBUG] Opportunity Form Validation Failed! Errors: {form.errors}")
        return render(request, self.template_name, {'form': form})


class CollaborationEditView(LoginRequiredMixin, View):
    template_name = 'marketplace/collaboration_form.html'

    def get(self, request, pk):
        collaboration = get_object_or_404(Collaboration, pk=pk, creator=request.user)
        form = CollaborationForm(instance=collaboration)
        return render(request, self.template_name, {'form': form, 'collaboration': collaboration})

    def post(self, request, pk):
        collaboration = get_object_or_404(Collaboration, pk=pk, creator=request.user)
        form = CollaborationForm(request.POST, instance=collaboration)
        if form.is_valid():
            collaboration = form.save()
            messages.success(request, f"Opportunity '{collaboration.title}' has been updated.")
            return redirect('marketplace:collaboration_detail', pk=collaboration.pk)
        return render(request, self.template_name, {'form': form, 'collaboration': collaboration})


class CollaborationDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        collaboration = get_object_or_404(Collaboration, pk=pk, creator=request.user)
        collaboration.delete()
        messages.success(request, "Opportunity deleted successfully.")
        return redirect('marketplace:collaboration_explore')


class ApplyView(LoginRequiredMixin, View):
    def post(self, request, pk):
        collaboration = get_object_or_404(Collaboration, pk=pk)
        if collaboration.creator == request.user:
            return HttpResponseForbidden("You cannot apply to your own project opportunity.")

        # Check status of collaboration
        if collaboration.status != Collaboration.Status.OPEN:
            messages.error(request, "This opportunity is no longer accepting applications.")
            return redirect('marketplace:collaboration_detail', pk=collaboration.pk)

        # Check existing application
        app, created = CollaborationApplication.objects.get_or_create(
            collaboration=collaboration,
            applicant=request.user,
            defaults={'message': request.POST.get('message', '').strip()}
        )
        if created:
            messages.success(request, "Your application has been submitted!")
        else:
            # If it was withdrawn, allow re-submitting by changing status and message
            if app.status == CollaborationApplication.Status.WITHDRAWN:
                app.status = CollaborationApplication.Status.PENDING
                app.message = request.POST.get('message', '').strip()
                app.save()
                messages.success(request, "Your application has been re-submitted!")
            else:
                messages.info(request, "You have already applied to this opportunity.")
                
        return redirect('marketplace:collaboration_detail', pk=collaboration.pk)


class WithdrawApplicationView(LoginRequiredMixin, View):
    def post(self, request, pk):
        application = get_object_or_404(CollaborationApplication, pk=pk, applicant=request.user)
        application.status = CollaborationApplication.Status.WITHDRAWN
        application.save()
        messages.success(request, "Your application was withdrawn.")
        return redirect('marketplace:collaboration_detail', pk=application.collaboration.pk)


class AcceptApplicationView(LoginRequiredMixin, View):
    def post(self, request, pk):
        application = get_object_or_404(CollaborationApplication, pk=pk, collaboration__creator=request.user)
        application.status = CollaborationApplication.Status.ACCEPTED
        application.save()
        messages.success(request, f"Application from {application.applicant.first_name} accepted!")
        return redirect('marketplace:collaboration_detail', pk=application.collaboration.pk)


class RejectApplicationView(LoginRequiredMixin, View):
    def post(self, request, pk):
        application = get_object_or_404(CollaborationApplication, pk=pk, collaboration__creator=request.user)
        application.status = CollaborationApplication.Status.REJECTED
        application.save()
        messages.success(request, f"Application from {application.applicant.first_name} rejected.")
        return redirect('marketplace:collaboration_detail', pk=application.collaboration.pk)


class MarketplaceDashboardView(LoginRequiredMixin, View):
    template_name = 'marketplace/my_dashboard.html'

    def get(self, request):
        my_collaborations = Collaboration.objects.filter(creator=request.user).order_by('-created_at')
        my_applications = CollaborationApplication.objects.filter(applicant=request.user).select_related('collaboration', 'collaboration__creator').order_by('-created_at')

        return render(request, self.template_name, {
            'my_collaborations': my_collaborations,
            'my_applications': my_applications
        })
