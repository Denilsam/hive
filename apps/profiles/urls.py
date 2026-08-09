from django.urls import path
from .views import (
    ProfileDetailView, ProfileEditView,
    EducationCreateView, EducationDeleteView,
    ExperienceCreateView, ExperienceDeleteView,
    UserSkillCreateView, UserSkillDeleteView,
    CertificateCreateView, CertificateDeleteView
)

app_name = 'profiles'

urlpatterns = [
    # Primary profiles endpoints
    path('profile/edit/', ProfileEditView.as_view(), name='profile_edit'),
    path('profile/<str:username>/', ProfileDetailView.as_view(), name='profile_detail'),
    
    # Sub-records endpoints (add/delete actions)
    path('profile/edit/education/add/', EducationCreateView.as_view(), name='education_add'),
    path('profile/edit/education/delete/<int:pk>/', EducationDeleteView.as_view(), name='education_delete'),
    
    path('profile/edit/experience/add/', ExperienceCreateView.as_view(), name='experience_add'),
    path('profile/edit/experience/delete/<int:pk>/', ExperienceDeleteView.as_view(), name='experience_delete'),
    
    path('profile/edit/skill/add/', UserSkillCreateView.as_view(), name='skill_add'),
    path('profile/edit/skill/delete/<int:pk>/', UserSkillDeleteView.as_view(), name='skill_delete'),
    
    path('profile/edit/certificate/add/', CertificateCreateView.as_view(), name='certificate_add'),
    path('profile/edit/certificate/delete/<int:pk>/', CertificateDeleteView.as_view(), name='certificate_delete'),
]
