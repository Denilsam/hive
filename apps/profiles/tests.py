from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
import datetime

from apps.profiles.models import Profile, Education, Experience, Skill, UserSkill, Certificate

User = get_user_model()


class ProfileSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create users
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='StrongPassword123!',
            first_name='User',
            last_name='One',
            account_type='STUDENT',
            is_verified=True,
            is_active=True
        )
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='StrongPassword123!',
            first_name='User',
            last_name='Two',
            account_type='CREATOR',
            is_verified=True,
            is_active=True
        )
        
        self.edit_url = reverse('profiles:profile_edit')

    def test_profile_auto_creation_signal(self):
        # User is created in setUp, verify Profile is auto-created
        self.assertIsNotNone(self.user1.profile)
        self.assertEqual(self.user1.profile.user, self.user1)

    def test_profile_completion_calculation(self):
        profile = self.user1.profile
        # Initially empty profile should have 0% completion (fields are empty/blank)
        self.assertEqual(profile.completion_percentage, 0)
        
        # Headline (15%) + Location (10%)
        profile.headline = "Python Developer"
        profile.location = "San Francisco, CA"
        profile.save()
        self.assertEqual(profile.completion_percentage, 25)
        
        # Add a skill (15%)
        skill = Skill.objects.create(name="Python")
        UserSkill.objects.create(user=self.user1, skill=skill, level="ADVANCED")
        self.assertEqual(profile.completion_percentage, 40)

    def test_profile_edit_view_authenticated(self):
        self.client.login(email='user1@example.com', password='StrongPassword123!')
        
        response = self.client.post(self.edit_url, {
            'first_name': 'UpdatedFirst',
            'last_name': 'UpdatedLast',
            'headline': 'Updated Headline',
            'bio': 'Updated Bio',
            'location': 'Updated Location',
            'phone_number': '1234567890'
        })
        self.assertEqual(response.status_code, 302)  # Redirects to detail view
        
        # Verify updates in DB
        self.user1.refresh_from_db()
        self.user1.profile.refresh_from_db()
        self.assertEqual(self.user1.first_name, 'UpdatedFirst')
        self.assertEqual(self.user1.profile.headline, 'Updated Headline')

    def test_profile_edit_permission_unauthenticated(self):
        # Verify anonymous users redirect to login
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 302)

    def test_public_profile_view(self):
        detail_url = reverse('profiles:profile_detail', kwargs={'username': self.user1.username})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User One")
        self.assertContains(response, "Student")

    def test_add_and_delete_education(self):
        self.client.login(email='user1@example.com', password='StrongPassword123!')
        add_edu_url = reverse('profiles:education_add')
        
        # Add Education
        response = self.client.post(add_edu_url, {
            'degree': 'BCA',
            'institution': 'Stanford',
            'field_of_study': 'CS',
            'start_year': 2021,
            'end_year': 2024,
            'description': 'BCA details'
        })
        self.assertEqual(response.status_code, 302)
        
        edu = Education.objects.get(user=self.user1)
        self.assertEqual(edu.degree, 'BCA')
        
        # Delete Education
        delete_url = reverse('profiles:education_delete', kwargs={'pk': edu.pk})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Education.objects.filter(user=self.user1).exists())

    def test_education_invalid_years(self):
        edu = Education(
            user=self.user1,
            degree='BCA',
            institution='Stanford',
            field_of_study='CS',
            start_year=2024,
            end_year=2021
        )
        with self.assertRaises(ValidationError):
            edu.full_clean()

    def test_add_and_delete_experience(self):
        self.client.login(email='user1@example.com', password='StrongPassword123!')
        add_exp_url = reverse('profiles:experience_add')
        
        # Add Experience
        response = self.client.post(add_exp_url, {
            'company_name': 'Google',
            'role': 'SWE',
            'employment_type': 'FULL_TIME',
            'start_date': '2021-01-01',
            'end_date': '2024-01-01',
            'currently_working': False,
            'description': 'Search work'
        })
        self.assertEqual(response.status_code, 302)
        
        exp = Experience.objects.get(user=self.user1)
        self.assertEqual(exp.company_name, 'Google')
        
        # Delete Experience
        delete_url = reverse('profiles:experience_delete', kwargs={'pk': exp.pk})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Experience.objects.filter(user=self.user1).exists())

    def test_experience_invalid_dates(self):
        exp = Experience(
            user=self.user1,
            company_name='Google',
            role='SWE',
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2021, 1, 1),
            currently_working=False
        )
        with self.assertRaises(ValidationError):
            exp.full_clean()

    def test_add_skill(self):
        self.client.login(email='user1@example.com', password='StrongPassword123!')
        add_skill_url = reverse('profiles:skill_add')
        
        response = self.client.post(add_skill_url, {
            'skill_name': 'Django',
            'level': 'EXPERT'
        })
        self.assertEqual(response.status_code, 302)
        
        us = UserSkill.objects.get(user=self.user1)
        self.assertEqual(us.skill.name, 'Django')
        self.assertEqual(us.level, 'EXPERT')

    def test_file_size_validation(self):
        # Create a mock file larger than 2MB
        large_file = SimpleUploadedFile(
            name="large.jpg",
            content=b"0" * (2 * 1024 * 1024 + 100),
            content_type="image/jpeg"
        )
        
        profile = self.user1.profile
        profile.profile_image = large_file
        
        with self.assertRaises(ValidationError):
            profile.full_clean()

    def test_profile_submodel_delete_permissions(self):
        exp = Experience.objects.create(
            user=self.user1,
            company_name='Meta',
            role='Engineer',
            start_date=datetime.date(2022, 1, 1),
            currently_working=True
        )
        delete_url = reverse('profiles:experience_delete', kwargs={'pk': exp.pk})

        # Non-owner cannot delete user1's experience
        self.client.login(email='user2@example.com', password='StrongPassword123!')
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Experience.objects.filter(pk=exp.pk).exists())

