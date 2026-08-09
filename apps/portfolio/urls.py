from django.urls import path
from .views import (
    PortfolioExploreView, PortfolioDetailView, ProjectDetailView,
    ProjectCreateView, ProjectEditView, ProjectDeleteView,
    ProjectLikeToggleView, ProjectCommentCreateView, ProjectCommentDeleteView,
    CertificateCreateView, CertificateDeleteView
)

app_name = 'portfolio'

urlpatterns = [
    # Search and explore projects
    path('portfolio/', PortfolioExploreView.as_view(), name='portfolio_explore'),
    
    # Project CRUD
    path('portfolio/create/', ProjectCreateView.as_view(), name='project_create'),
    path('portfolio/<int:pk>/edit/', ProjectEditView.as_view(), name='project_edit'),
    path('portfolio/<int:pk>/delete/', ProjectDeleteView.as_view(), name='project_delete'),
    
    # Portfolio user detail
    path('portfolio/<str:username>/', PortfolioDetailView.as_view(), name='portfolio_detail'),
    
    # Project details direct link
    path('project/<slug:slug>/', ProjectDetailView.as_view(), name='project_detail'),
    
    # Certificate CRUD
    path('portfolio/certificate/add/', CertificateCreateView.as_view(), name='certificate_add'),
    path('portfolio/certificate/<int:pk>/delete/', CertificateDeleteView.as_view(), name='certificate_delete'),
    
    # AJAX Actions
    path('project/<int:pk>/like/', ProjectLikeToggleView.as_view(), name='project_like_toggle'),
    path('project/<int:pk>/comment/', ProjectCommentCreateView.as_view(), name='project_comment_create'),
    path('project/comment/<int:pk>/delete/', ProjectCommentDeleteView.as_view(), name='project_comment_delete'),
]
