from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import json

from .models import Follow, ConnectionRequest, Connection
from apps.profiles.models import Profile, Skill, UserSkill

User = get_user_model()


class ConnectionSystemTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create users
        self.user1 = User.objects.create_user(
            email='alice@example.com',
            password='StrongPassword123!',
            first_name='Alice',
            last_name='Smith',
            account_type='STUDENT',
            is_verified=True,
            is_active=True
        )
        self.user2 = User.objects.create_user(
            email='bob@example.com',
            password='StrongPassword123!',
            first_name='Bob',
            last_name='Jones',
            account_type='CREATOR',
            is_verified=True,
            is_active=True
        )
        self.user3 = User.objects.create_user(
            email='charlie@example.com',
            password='StrongPassword123!',
            first_name='Charlie',
            last_name='Brown',
            account_type='FREELANCER',
            is_verified=True,
            is_active=True
        )

        # Get automatically created profiles and update fields
        self.profile1 = self.user1.profile
        self.profile1.headline = 'Student Developer'
        self.profile1.save()

        self.profile2 = self.user2.profile
        self.profile2.headline = 'Content Creator'
        self.profile2.save()

        self.profile3 = self.user3.profile
        self.profile3.headline = 'Freelance Designer'
        self.profile3.save()

        self.skill_python = Skill.objects.create(name='Python')
        self.skill_design = Skill.objects.create(name='Design')

        UserSkill.objects.create(user=self.user1, skill=self.skill_python)
        UserSkill.objects.create(user=self.user3, skill=self.skill_design)

        # URLs
        self.network_url = reverse('connections:network')
        self.requests_url = reverse('connections:requests')

    def test_follow_self_prevented(self):
        follow = Follow(follower=self.user1, following=self.user1)
        with self.assertRaises(ValidationError):
            follow.full_clean()

    def test_duplicate_follow_prevented(self):
        Follow.objects.create(follower=self.user1, following=self.user2)
        duplicate = Follow(follower=self.user1, following=self.user2)
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_connection_request_self_prevented(self):
        req = ConnectionRequest(sender=self.user1, receiver=self.user1, status='PENDING')
        with self.assertRaises(ValidationError):
            req.full_clean()

    def test_duplicate_pending_request_prevented(self):
        ConnectionRequest.objects.create(sender=self.user1, receiver=self.user2, status='PENDING')
        
        # Second request from same sender to same receiver should raise ValidationError
        dup = ConnectionRequest(sender=self.user1, receiver=self.user2, status='PENDING')
        with self.assertRaises(ValidationError):
            dup.full_clean()

        # Request from receiver to sender when there is already a pending request from sender should raise ValidationError
        reverse_dup = ConnectionRequest(sender=self.user2, receiver=self.user1, status='PENDING')
        with self.assertRaises(ValidationError):
            reverse_dup.full_clean()

    def test_connection_request_already_connected_prevented(self):
        # Establish connection
        u1, u2 = (self.user1, self.user2) if self.user1.id < self.user2.id else (self.user2, self.user1)
        Connection.objects.create(user1=u1, user2=u2)

        req = ConnectionRequest(sender=self.user1, receiver=self.user2, status='PENDING')
        with self.assertRaises(ValidationError):
            req.full_clean()

    def test_connection_ordering_enforced(self):
        # Create connection where user1.id > user2.id to verify swap
        higher_user = self.user1 if self.user1.id > self.user2.id else self.user2
        lower_user = self.user2 if self.user1.id > self.user2.id else self.user1

        conn = Connection.objects.create(user1=higher_user, user2=lower_user)
        
        # Verify swap was enforced
        self.assertEqual(conn.user1, lower_user)
        self.assertEqual(conn.user2, higher_user)

    def test_duplicate_connections_prevented(self):
        u1, u2 = (self.user1, self.user2) if self.user1.id < self.user2.id else (self.user2, self.user1)
        Connection.objects.create(user1=u1, user2=u2)

        duplicate = Connection(user1=u1, user2=u2)
        with self.assertRaises(ValidationError):
            duplicate.full_clean()

    def test_network_discovery_view_search(self):
        self.client.login(email='alice@example.com', password='StrongPassword123!')
        
        # Test search by name
        response = self.client.get(self.network_url, {'q': 'Charlie'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.user3, response.context['users'])
        self.assertNotIn(self.user2, response.context['users'])

    def test_ajax_follow_toggle(self):
        self.client.login(email='alice@example.com', password='StrongPassword123!')
        follow_url = reverse('connections:follow_toggle', kwargs={'user_id': self.user2.id})

        # Self-follow attempt returns 400
        self_follow_url = reverse('connections:follow_toggle', kwargs={'user_id': self.user1.id})
        res_self = self.client.post(self_follow_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(res_self.status_code, 400)

        # Follow
        response = self.client.post(follow_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertTrue(data['following'])
        self.assertEqual(data['follower_count'], 1)
        self.assertEqual(data['following_count'], 1)
        self.assertTrue(Follow.objects.filter(follower=self.user1, following=self.user2).exists())

        # Unfollow
        response = self.client.post(follow_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertFalse(data['following'])
        self.assertEqual(data['follower_count'], 0)
        self.assertEqual(data['following_count'], 0)
        self.assertFalse(Follow.objects.filter(follower=self.user1, following=self.user2).exists())

    def test_ajax_connection_request_lifecycle(self):
        self.client.login(email='alice@example.com', password='StrongPassword123!')
        
        # 1. Send Request
        send_url = reverse('connections:send_request', kwargs={'user_id': self.user2.id})
        response = self.client.post(send_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        
        req = ConnectionRequest.objects.filter(sender=self.user1, receiver=self.user2, status='PENDING').first()
        self.assertIsNotNone(req)

        # 2. Cancel Request (as Alice)
        cancel_url = reverse('connections:cancel_request', kwargs={'pk': req.id})
        response = self.client.post(cancel_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        
        req.refresh_from_db()
        self.assertEqual(req.status, 'CANCELLED')

        # 3. Send request again and Accept (as Bob)
        req.status = 'PENDING'
        req.save()

        self.client.login(email='bob@example.com', password='StrongPassword123!')
        accept_url = reverse('connections:accept_request', kwargs={'pk': req.id})
        response = self.client.post(accept_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)

        req.refresh_from_db()
        self.assertEqual(req.status, 'ACCEPTED')
        
        u1, u2 = (self.user1, self.user2) if self.user1.id < self.user2.id else (self.user2, self.user1)
        self.assertTrue(Connection.objects.filter(user1=u1, user2=u2).exists())
        self.assertTrue(Follow.objects.filter(follower=self.user1, following=self.user2).exists())
        self.assertTrue(Follow.objects.filter(follower=self.user2, following=self.user1).exists())

    def test_user_profile_followers_and_following_lists(self):
        # Alice (user1) follows Bob (user2). Charlie (user3) follows Bob (user2).
        Follow.objects.create(follower=self.user1, following=self.user2)
        Follow.objects.create(follower=self.user3, following=self.user2)

        # Charlie logs in and views Bob's followers list URL
        self.client.login(email='charlie@example.com', password='StrongPassword123!')
        bob_followers_url = reverse('connections:user_followers', kwargs={'username': self.user2.username})
        response = self.client.get(bob_followers_url)
        self.assertEqual(response.status_code, 200)
        
        # Verify context contains Bob's followers (Alice and Charlie), NOT Charlie's followers
        self.assertEqual(response.context['profile_user'], self.user2)
        self.assertIn(self.user1, response.context['followers'])
        self.assertIn(self.user3, response.context['followers'])

        # Charlie views Alice's following list URL (Alice follows Bob)
        alice_following_url = reverse('connections:user_following', kwargs={'username': self.user1.username})
        response_following = self.client.get(alice_following_url)
        self.assertEqual(response_following.status_code, 200)
        self.assertEqual(response_following.context['profile_user'], self.user1)
        self.assertIn(self.user2, response_following.context['following'])
