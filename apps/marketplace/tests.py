from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import decimal

from .models import Collaboration, CollaborationSkill, CollaborationApplication
from apps.profiles.models import Skill

User = get_user_model()


class MarketplaceSystemTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create users
        self.user1 = User.objects.create_user(
            email='alice@example.com',
            password='StrongPassword123!',
            first_name='Alice',
            last_name='Smith',
            account_type='STUDENT',
            is_active=True
        )
        self.user2 = User.objects.create_user(
            email='bob@example.com',
            password='StrongPassword123!',
            first_name='Bob',
            last_name='Jones',
            account_type='CREATOR',
            is_active=True
        )
        self.user3 = User.objects.create_user(
            email='charlie@example.com',
            password='StrongPassword123!',
            first_name='Charlie',
            last_name='Brown',
            is_active=True
        )

        # Create base collaboration
        self.collab = Collaboration.objects.create(
            creator=self.user1,
            title="EdTech Platform",
            description="Building a Django education app",
            category="Software Development",
            project_type="STARTUP",
            budget_type="PAID",
            budget_amount=decimal.Decimal('1500.00'),
            duration="3 Months",
            status="OPEN"
        )
        self.skill_python = Skill.objects.create(name="Python")
        self.skill_react = Skill.objects.create(name="React")
        
        CollaborationSkill.objects.create(collaboration=self.collab, skill=self.skill_python)

        self.explore_url = reverse('marketplace:collaboration_explore')
        self.create_url = reverse('marketplace:collaboration_create')

    def test_collaboration_creation_and_defaults(self):
        col = Collaboration.objects.create(
            creator=self.user2,
            title="Design System",
            description="Designing sleek UI widgets",
            category="Design",
            project_type="PERSONAL_PROJECT",
            budget_type="UNPAID"
        )
        # Verify defaults
        self.assertEqual(col.status, 'OPEN')
        self.assertEqual(col.budget_type, 'UNPAID')

    def test_collaboration_edit_delete_creator_permission(self):
        self.client.login(email='bob@example.com', password='StrongPassword123!')
        
        # Try editing Alice's opportunity (should return 404 since creator check fails)
        edit_url = reverse('marketplace:collaboration_edit', kwargs={'pk': self.collab.pk})
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 404)

        # Try deleting Alice's opportunity
        delete_url = reverse('marketplace:collaboration_delete', kwargs={'pk': self.collab.pk})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 404)

        # Log in as Alice and delete successfully
        self.client.login(email='alice@example.com', password='StrongPassword123!')
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Collaboration.objects.filter(id=self.collab.id).exists())

    def test_application_flow_and_permissions(self):
        # 1. User1 (creator) tries to apply to own opportunity via model validation
        app_self = CollaborationApplication(
            collaboration=self.collab,
            applicant=self.user1,
            message="Pick me!"
        )
        with self.assertRaises(ValidationError):
            app_self.full_clean()

        # 2. Bob applies successfully
        self.client.login(email='bob@example.com', password='StrongPassword123!')
        apply_url = reverse('marketplace:apply', kwargs={'pk': self.collab.pk})
        response = self.client.post(apply_url, {'message': "I am an expert Django dev."})
        self.assertEqual(response.status_code, 302)
        
        app = CollaborationApplication.objects.filter(collaboration=self.collab, applicant=self.user2).first()
        self.assertIsNotNone(app)
        self.assertEqual(app.status, 'PENDING')

        # 3. Prevent duplicate application
        dup_response = self.client.post(apply_url, {'message': "Another message."})
        self.assertEqual(dup_response.status_code, 302)
        self.assertEqual(CollaborationApplication.objects.filter(collaboration=self.collab, applicant=self.user2).count(), 1)

        # 4. Creator Alice accepts Bob's application
        self.client.login(email='alice@example.com', password='StrongPassword123!')
        accept_url = reverse('marketplace:accept_application', kwargs={'pk': app.id})
        response = self.client.post(accept_url)
        self.assertEqual(response.status_code, 302)
        
        app.refresh_from_db()
        self.assertEqual(app.status, 'ACCEPTED')

    def test_search_and_filtering(self):
        # Additional collab for filter testing
        col2 = Collaboration.objects.create(
            creator=self.user2,
            title="Logo Redesign",
            description="Figma UI project",
            category="Design",
            project_type="FREELANCE",
            budget_type="EQUITY",
            status="OPEN"
        )
        CollaborationSkill.objects.create(collaboration=col2, skill=self.skill_react)

        # 1. Keyword search (q='Figma')
        response = self.client.get(self.explore_url, {'q': 'Figma'})
        self.assertEqual(response.status_code, 200)
        collabs = list(response.context['collaborations'])
        self.assertIn(col2, collabs)
        self.assertNotIn(self.collab, collabs)

        # 2. Category filter
        response = self.client.get(self.explore_url, {'category': 'Design'})
        self.assertEqual(response.status_code, 200)
        collabs = list(response.context['collaborations'])
        self.assertIn(col2, collabs)
        self.assertNotIn(self.collab, collabs)

        # 3. Budget type filter
        response = self.client.get(self.explore_url, {'budget_type': 'PAID'})
        self.assertEqual(response.status_code, 200)
        collabs = list(response.context['collaborations'])
        self.assertIn(self.collab, collabs)
        self.assertNotIn(col2, collabs)

        # 4. Skill filter
        response = self.client.get(self.explore_url, {'skill': 'React'})
        self.assertEqual(response.status_code, 200)
        collabs = list(response.context['collaborations'])
        self.assertIn(col2, collabs)
        self.assertNotIn(self.collab, collabs)

    def test_collaboration_delete_permissions(self):
        delete_url = reverse('marketplace:collaboration_delete', kwargs={'pk': self.collab.pk})

        # 1. Non-creator cannot delete (returns 404 due to creator filter)
        self.client.login(email='bob@example.com', password='StrongPassword123!')
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Collaboration.objects.filter(pk=self.collab.pk).exists())

        # 2. Creator can delete via POST
        self.client.login(email='alice@example.com', password='StrongPassword123!')
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Collaboration.objects.filter(pk=self.collab.pk).exists())

