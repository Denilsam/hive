from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.urls import reverse
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import Project, ProjectImage, ProjectLike, ProjectComment, Certificate, ProjectView
from .forms import ProjectForm, ProjectCommentForm, CertificateForm
from apps.profiles.models import Skill

User = get_user_model()


class PortfolioExploreView(View):
    template_name = 'portfolio/portfolio_home.html'

    def get(self, request):
        queryset = Project.objects.all().select_related(
            'owner', 'owner__profile'
        ).prefetch_related('technologies')
        
        # Enforce visibility rules
        if request.user.is_authenticated:
            from django.db.models import Q
            from apps.connections.models import Connection
            
            connected_user_ids = list(Connection.objects.filter(
                Q(user1=request.user) | Q(user2=request.user)
            ).values_list('user1_id', 'user2_id'))
            
            connected_ids = set()
            for u1, u2 in connected_user_ids:
                connected_ids.add(u1)
                connected_ids.add(u2)
            connected_ids.discard(request.user.id)
            
            queryset = queryset.filter(
                Q(owner=request.user) |
                Q(visibility=Project.Visibility.PUBLIC) |
                Q(visibility=Project.Visibility.CONNECTIONS, owner_id__in=connected_ids)
            )
        else:
            queryset = queryset.filter(visibility=Project.Visibility.PUBLIC)
        
        # Search parameters
        q = request.GET.get('q', '').strip()
        if q:
            queryset = queryset.filter(
                models.Q(title__icontains=q) |
                models.Q(technologies__name__icontains=q) |
                models.Q(category__icontains=q) |
                models.Q(owner__first_name__icontains=q) |
                models.Q(owner__last_name__icontains=q)
            ).distinct()
            
        # Filters
        category = request.GET.get('category', '').strip()
        if category:
            queryset = queryset.filter(category=category)
            
        tech = request.GET.get('technology', '').strip()
        if tech:
            queryset = queryset.filter(technologies__name__iexact=tech)
            
        featured = request.GET.get('featured', '').strip()
        if featured == 'true':
            queryset = queryset.filter(is_featured=True)

        # Retrieve distinct skills list for search dropdown
        available_skills = Skill.objects.filter(projects__isnull=False).distinct()

        return render(request, self.template_name, {
            'projects': queryset,
            'available_skills': available_skills,
            'categories': Project.Category.choices,
            'selected_category': category,
            'selected_tech': tech,
            'selected_featured': featured == 'true',
            'query': q
        })


class PortfolioDetailView(View):
    template_name = 'portfolio/portfolio_detail.html'

    def get(self, request, username):
        user = get_object_or_404(User, username=username)
        
        # Determine which projects the viewer is allowed to see
        if request.user == user:
            projects = user.projects.all().prefetch_related('technologies', 'likes', 'comments')
        else:
            from django.db.models import Q
            if request.user.is_authenticated:
                from apps.connections.models import Connection
                is_connected = Connection.objects.filter(
                    Q(user1=request.user, user2=user) |
                    Q(user1=user, user2=request.user)
                ).exists()
                if is_connected:
                    allowed_visibilities = [Project.Visibility.PUBLIC, Project.Visibility.CONNECTIONS]
                else:
                    allowed_visibilities = [Project.Visibility.PUBLIC]
            else:
                allowed_visibilities = [Project.Visibility.PUBLIC]
            
            projects = user.projects.filter(visibility__in=allowed_visibilities).prefetch_related('technologies', 'likes', 'comments')
        
        # Divide into featured and regular projects
        featured_projects = projects.filter(is_featured=True)
        regular_projects = projects.filter(is_featured=False)
        
        # Calculate stats
        total_projects = projects.count()
        total_likes = sum(p.likes.count() for p in projects)
        
        # Extract unique skills used across projects
        used_skills = Skill.objects.filter(projects__owner=user, projects__in=projects).distinct()
        
        # Fetch certificates for the portfolio owner
        certificates = user.portfolio_certificates.all().order_by('-issue_date')
        
        # Fetch UserSkills for the portfolio owner
        user_skills = user.userskill_set.all().select_related('skill')

        return render(request, self.template_name, {
            'portfolio_user': user,
            'profile': getattr(user, 'profile', None),
            'featured_projects': featured_projects,
            'all_projects': regular_projects,
            'total_projects': total_projects,
            'total_likes': total_likes,
            'used_skills': used_skills,
            'certificates': certificates,
            'user_skills': user_skills,
            'is_own_portfolio': (request.user == user)
        })


class ProjectDetailView(DetailView):
    model = Project
    template_name = 'portfolio/project_detail.html'
    context_object_name = 'project'

    def get(self, request, *args, **kwargs):
        # We need to override get to ensure we run get_object and track views safely
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_object(self, queryset=None):
        project = super().get_object(queryset)
        request = self.request
        
        # Enforce visibility rules
        if project.visibility == Project.Visibility.PRIVATE:
            if request.user != project.owner:
                raise Http404("You do not have permission to view this project.")
        elif project.visibility == Project.Visibility.CONNECTIONS:
            if request.user != project.owner:
                if not request.user.is_authenticated:
                    raise Http404("You do not have permission to view this project.")
                from django.db.models import Q
                from apps.connections.models import Connection
                is_connected = Connection.objects.filter(
                    Q(user1=request.user, user2=project.owner) |
                    Q(user1=project.owner, user2=request.user)
                ).exists()
                if not is_connected:
                    raise Http404("You do not have permission to view this project.")
                    
        # Track project view
        visitor = request.user if request.user.is_authenticated else None
        ProjectView.objects.create(project=project, visitor=visitor)
        
        return project

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object
        
        context['comments'] = project.comments.select_related('user', 'user__profile').all()
        context['comment_form'] = ProjectCommentForm()
        context['images'] = project.images.all()
        
        if self.request.user.is_authenticated:
            context['is_liked'] = project.likes.filter(user=self.request.user).exists()
        else:
            context['is_liked'] = False
            
        return context


class ProjectCreateView(LoginRequiredMixin, View):
    template_name = 'portfolio/project_form.html'

    def get(self, request):
        form = ProjectForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ProjectForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                project = form.save(commit=False)
                project.owner = request.user
                project.full_clean()
                project.save()
                form.save_m2m() # Saves tech_tags
                messages.success(request, f"Project '{project.title}' successfully published!")
                return redirect('portfolio:portfolio_detail', username=request.user.username)
            except ValidationError as e:
                form.add_error(None, e)
        return render(request, self.template_name, {'form': form})


class ProjectEditView(LoginRequiredMixin, View):
    template_name = 'portfolio/project_form.html'

    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk, owner=request.user)
        form = ProjectForm(instance=project)
        return render(request, self.template_name, {'form': form, 'project': project})

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk, owner=request.user)
        form = ProjectForm(request.POST, request.FILES, instance=project)
        if form.is_valid():
            try:
                updated_project = form.save(commit=False)
                updated_project.full_clean()
                updated_project.save()
                form.save_m2m()
                messages.success(request, f"Project '{updated_project.title}' has been updated.")
                return redirect('portfolio:portfolio_detail', username=request.user.username)
            except ValidationError as e:
                form.add_error(None, e)
        return render(request, self.template_name, {'form': form, 'project': project})


class ProjectDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk, owner=request.user)
        project.delete()
        messages.success(request, "Project deleted from portfolio.")
        return redirect('portfolio:portfolio_detail', username=request.user.username)


class CertificateCreateView(LoginRequiredMixin, View):
    template_name = 'portfolio/certificate_form.html'

    def get(self, request):
        form = CertificateForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = CertificateForm(request.POST, request.FILES)
        if form.is_valid():
            cert = form.save(commit=False)
            cert.user = request.user
            cert.save()
            messages.success(request, f"Certificate '{cert.title}' successfully added!")
            return redirect('portfolio:portfolio_detail', username=request.user.username)
        return render(request, self.template_name, {'form': form})


class CertificateDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        cert = get_object_or_404(Certificate, pk=pk, user=request.user)
        cert.delete()
        messages.success(request, "Certificate removed.")
        return redirect('portfolio:portfolio_detail', username=request.user.username)


# --- AJAX Views responding in JSON ---

class ProjectLikeToggleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        like, created = ProjectLike.objects.get_or_create(user=request.user, project=project)
        
        if not created:
            like.delete()
            liked = False
        else:
            liked = True
            
        return JsonResponse({
            'success': True,
            'liked': liked,
            'likes_count': project.likes.count()
        })


class ProjectCommentCreateView(LoginRequiredMixin, View):
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        form = ProjectCommentForm(request.POST)
        
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.project = project
            comment.save()
            
            avatar_url = comment.user.profile.profile_image.url if comment.user.profile.profile_image else ""
            
            return JsonResponse({
                'success': True,
                'comment': {
                    'id': comment.id,
                    'author_name': f"{comment.user.first_name} {comment.user.last_name}",
                    'author_username': comment.user.username,
                    'author_avatar': avatar_url,
                    'content': comment.content,
                    'created_at': comment.created_at.strftime('%b %d, %Y, %I:%M %p'),
                    'delete_url': reverse('portfolio:project_comment_delete', kwargs={'pk': comment.pk})
                }
            })
            
        return JsonResponse({
            'success': False,
            'errors': form.errors
        })


class ProjectCommentDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        comment = get_object_or_404(ProjectComment, pk=pk, user=request.user)
        comment.delete()
        return JsonResponse({
            'success': True
        })
