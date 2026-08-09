from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import ValidationError

from .models import Notification
from .services import create_notification, mark_notification_read, mark_all_read
from apps.posts.models import Post, Like, Comment
from apps.connections.models import Follow, ConnectionRequest

User = get_user_model()


class NotificationsSystemTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Create users
        self.user1 = User.objects.create_user(
            email='alice@example.com',
            password='StrongPassword123!',
            first_name='Alice',
            last_name='Smith',
            is_active=True
        )
        self.user2 = User.objects.create_user(
            email='bob@example.com',
            password='StrongPassword123!',
            first_name='Bob',
            last_name='Jones',
            is_active=True
        )
        self.user3 = User.objects.create_user(
            email='charlie@example.com',
            password='StrongPassword123!',
            first_name='Charlie',
            last_name='Brown',
            is_active=True
        )

        # Create a post for user1 to test post engagement notifications
        self.post = Post.objects.create(
            author=self.user1,
            content="Testing notifications"
        )

    def test_notification_creation_and_read_status(self):
        # 1. Create notification
        notif = create_notification(
            receiver=self.user1,
            sender=self.user2,
            notification_type='MESSAGE',
            message="Hey Alice!",
            related_url="/chat/"
        )
        self.assertIsNotNone(notif)
        self.assertEqual(notif.receiver, self.user1)
        self.assertEqual(notif.sender, self.user2)
        self.assertEqual(notif.notification_type, 'MESSAGE')
        self.assertFalse(notif.is_read)

        # 2. Mark specific read
        success = mark_notification_read(notif.id, self.user1)
        self.assertTrue(success)
        notif.refresh_from_db()
        self.assertTrue(notif.is_read)

        # 3. Mark all read
        notif2 = create_notification(receiver=self.user1, sender=self.user2, notification_type='LIKE', message="Liked")
        notif3 = create_notification(receiver=self.user1, sender=self.user2, notification_type='COMMENT', message="Commented")
        self.assertEqual(Notification.objects.filter(receiver=self.user1, is_read=False).count(), 2)

        mark_all_read(self.user1)
        self.assertEqual(Notification.objects.filter(receiver=self.user1, is_read=False).count(), 0)

    def test_permissions_only_receiver_can_modify(self):
        notif = create_notification(receiver=self.user1, sender=self.user2, notification_type='LIKE', message="Liked")
        
        # Charlie (user3) tries to mark Alice's notification as read
        success = mark_notification_read(notif.id, self.user3)
        self.assertFalse(success)
        notif.refresh_from_db()
        self.assertFalse(notif.is_read)

        # HTTP level permission check
        self.client.login(email='charlie@example.com', password='StrongPassword123!')
        read_url = reverse('notifications:notification_read', kwargs={'pk': notif.id})
        response = self.client.post(read_url)
        self.assertEqual(response.status_code, 403)

    def test_post_like_and_comment_notifications(self):
        # 1. Bob likes Alice's post
        Like.objects.create(user=self.user2, post=self.post)
        
        # Verify notification created for Alice
        like_notif = Notification.objects.filter(receiver=self.user1, notification_type='LIKE').first()
        self.assertIsNotNone(like_notif)
        self.assertEqual(like_notif.sender, self.user2)
        self.assertIn("liked your post", like_notif.message)

        # 2. Bob comments on Alice's post
        Comment.objects.create(user=self.user2, post=self.post, content="Cool post!")
        comment_notif = Notification.objects.filter(receiver=self.user1, notification_type='COMMENT').first()
        self.assertIsNotNone(comment_notif)
        self.assertEqual(comment_notif.sender, self.user2)
        self.assertIn("commented on your post", comment_notif.message)

    def test_connection_and_follow_notifications(self):
        # 1. Bob follows Alice
        Follow.objects.create(follower=self.user2, following=self.user1)
        follow_notif = Notification.objects.filter(receiver=self.user1, notification_type='FOLLOW').first()
        self.assertIsNotNone(follow_notif)
        self.assertEqual(follow_notif.sender, self.user2)
        self.assertIn("started following you", follow_notif.message)

        # 2. Bob sends connection request to Alice
        req = ConnectionRequest.objects.create(sender=self.user2, receiver=self.user1, status='PENDING')
        req_notif = Notification.objects.filter(receiver=self.user1, notification_type='CONNECTION_REQUEST').first()
        self.assertIsNotNone(req_notif)
        self.assertEqual(req_notif.sender, self.user2)

        # 3. Alice accepts connection request -> notifies Bob
        req.status = 'ACCEPTED'
        req.save()
        accept_notif = Notification.objects.filter(receiver=self.user2, notification_type='CONNECTION_ACCEPTED').first()
        self.assertIsNotNone(accept_notif)
        self.assertEqual(accept_notif.sender, self.user1)

    def test_notification_list_view_without_profile_image(self):
        # Create comment and like notifications where sender has no profile_image
        create_notification(receiver=self.user1, sender=self.user2, notification_type='COMMENT', message="Bob commented on your post.")
        create_notification(receiver=self.user1, sender=self.user2, notification_type='LIKE', message="Bob liked your post.")
        
        self.client.login(email='alice@example.com', password='StrongPassword123!')
        response = self.client.get(reverse('notifications:notification_list'))
        self.assertEqual(response.status_code, 200)

    def test_follow_back_state_synchronization(self):
        # Bob (user2) follows Alice (user1), creating a FOLLOW notification for Alice
        Follow.objects.create(follower=self.user2, following=self.user1)

        self.client.login(email='alice@example.com', password='StrongPassword123!')
        response = self.client.get(reverse('notifications:notification_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Follow Back")
        self.assertNotContains(response, ">Following<")

        # Now Alice follows Bob back via FollowToggleView
        follow_url = reverse('connections:follow_toggle', kwargs={'user_id': self.user2.id})
        toggle_res = self.client.post(follow_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(toggle_res.status_code, 200)
        self.assertTrue(toggle_res.json()['following'])

        # Refresh Notifications page - must show "Following" and NOT "Follow Back"
        response_after = self.client.get(reverse('notifications:notification_list'))
        self.assertEqual(response_after.status_code, 200)
        self.assertContains(response_after, "Following")
        self.assertNotContains(response_after, "Follow Back")

