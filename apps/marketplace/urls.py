from django.urls import path
from .views import (
    CollaborationExploreView, CollaborationDetailView, CollaborationCreateView, CollaborationEditView,
    CollaborationDeleteView, ApplyView, WithdrawApplicationView, AcceptApplicationView,
    RejectApplicationView, MarketplaceDashboardView
)

app_name = 'marketplace'

urlpatterns = [
    # Discover opportunities
    path('marketplace/', CollaborationExploreView.as_view(), name='collaboration_explore'),
    
    # Collaboration CRUD
    path('marketplace/create/', CollaborationCreateView.as_view(), name='collaboration_create'),
    path('marketplace/publish/', CollaborationCreateView.as_view(), name='publish_opportunity'),
    path('marketplace/<int:pk>/edit/', CollaborationEditView.as_view(), name='collaboration_edit'),
    path('marketplace/<int:pk>/delete/', CollaborationDeleteView.as_view(), name='collaboration_delete'),
    
    # Collaboration Details
    path('marketplace/<int:pk>/', CollaborationDetailView.as_view(), name='collaboration_detail'),
    
    # Application actions
    path('marketplace/<int:pk>/apply/', ApplyView.as_view(), name='apply'),
    path('marketplace/application/<int:pk>/withdraw/', WithdrawApplicationView.as_view(), name='withdraw_application'),
    path('marketplace/application/<int:pk>/accept/', AcceptApplicationView.as_view(), name='accept_application'),
    path('marketplace/application/<int:pk>/reject/', RejectApplicationView.as_view(), name='reject_application'),
    
    # Dashboard
    path('marketplace/dashboard/', MarketplaceDashboardView.as_view(), name='marketplace_dashboard'),
]
