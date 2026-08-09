from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
import json

from apps.posts.models import Post, Like, Comment, SavedPost

User = get_user_model()


class PostSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create users
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='StrongPassword123!',
            first_name='Feed',
            last_name='User1',
            account_type='STUDENT',
            is_verified=True,
            is_active=True
        )
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='StrongPassword123!',
            first_name='Feed',
            last_name='User2',
            account_type='CREATOR',
            is_verified=True,
            is_active=True
        )
        
        self.create_url = reverse('posts:create')
        self.feed_url = reverse('posts:feed')

    def test_post_creation_requires_authentication(self):
        # GET create post should redirect to login
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, 302)

    def test_post_creation_authenticated(self):
        self.client.login(email='user1@example.com', password='StrongPassword123!')
        
        response = self.client.post(self.create_url, {
            'content': 'This is a test post content',
        })
        self.assertEqual(response.status_code, 302)  # Redirects to feed
        
        # Verify in DB
        post = Post.objects.first()
        self.assertIsNotNone(post)
        self.assertEqual(post.author, self.user1)
        self.assertEqual(post.content, 'This is a test post content')
        self.assertEqual(post.post_type, 'TEXT')

    def test_post_validation_empty_content_and_media(self):
        # A post cannot have both content, image, and video empty
        post = Post(author=self.user1, post_type='TEXT')
        with self.assertRaises(ValidationError):
            post.full_clean()

    def test_feed_ordering_latest_first(self):
        self.client.login(email='user1@example.com', password='StrongPassword123!')
        
        # Create posts at different times
        post1 = Post.objects.create(author=self.user1, content='First Post', post_type='TEXT')
        post2 = Post.objects.create(author=self.user1, content='Second Post', post_type='TEXT')
        
        response = self.client.get(self.feed_url)
        self.assertEqual(response.status_code, 200)
        
        # Post2 should come first (reverse chronological order)
        posts_in_context = list(response.context['posts'])
        self.assertEqual(posts_in_context[0], post2)
        self.assertEqual(posts_in_context[1], post1)

    def test_like_toggle_view(self):
        self.client.login(email='user1@example.com', password='StrongPassword123!')
        post = Post.objects.create(author=self.user1, content='Like me!', post_type='TEXT')
        like_url = reverse('posts:like_toggle', kwargs={'pk': post.pk})
        
        # Like the post
        response = self.client.post(like_url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['liked'])
        self.assertEqual(data['likes_count'], 1)
        self.assertTrue(Like.objects.filter(user=self.user1, post=post).exists())
        
        # Unlike the post
        response = self.client.post(like_url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['liked'])
        self.assertEqual(data['likes_count'], 0)
        self.assertFalse(Like.objects.filter(user=self.user1, post=post).exists())

    def test_duplicate_like_prevention(self):
        post = Post.objects.create(author=self.user1, content='Duplicate check', post_type='TEXT')
        Like.objects.create(user=self.user1, post=post)
        
        # Trying to create another Like manually for same user + post should raise integrity error
        with self.assertRaises(Exception):
            Like.objects.create(user=self.user1, post=post)

    def test_comment_creation_ajax(self):
        self.client.login(email='user1@example.com', password='StrongPassword123!')
        post = Post.objects.create(author=self.user2, content='Comment on this', post_type='TEXT')
        comment_url = reverse('posts:comment_create', kwargs={'pk': post.pk})
        
        # Submit comment
        response = self.client.post(comment_url, {'content': 'My thoughts exactly!'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['comment']['content'], 'My thoughts exactly!')
        
        # Check DB
        self.assertTrue(Comment.objects.filter(user=self.user1, post=post, content='My thoughts exactly!').exists())

    def test_comment_deletion_unauthorized_denied(self):
        # user1 creates comment, user2 tries to delete it
        post = Post.objects.create(author=self.user1, content='Comment block', post_type='TEXT')
        comment = Comment.objects.create(user=self.user1, post=post, content='My comment')
        
        self.client.login(email='user2@example.com', password='StrongPassword123!')
        delete_url = reverse('posts:comment_delete', kwargs={'pk': comment.pk})
        
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 404)  # Get_object_or_454 filters by user=request.user, so returns 404
        self.assertTrue(Comment.objects.filter(pk=comment.pk).exists())

    def test_comment_deletion_authorized(self):
        post = Post.objects.create(author=self.user1, content='Comment delete', post_type='TEXT')
        comment = Comment.objects.create(user=self.user1, post=post, content='Delete this')
        
        self.client.login(email='user1@example.com', password='StrongPassword123!')
        delete_url = reverse('posts:comment_delete', kwargs={'pk': comment.pk})
        
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())

    def test_save_post_toggle_view(self):
        self.client.login(email='user1@example.com', password='StrongPassword123!')
        post = Post.objects.create(author=self.user2, content='Save this post', post_type='TEXT')
        save_url = reverse('posts:save_toggle', kwargs={'pk': post.pk})
        
        # Save post
        response = self.client.post(save_url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['saved'])
        self.assertTrue(SavedPost.objects.filter(user=self.user1, post=post).exists())
        
        # Unsave post
        response = self.client.post(save_url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['saved'])
        self.assertFalse(SavedPost.objects.filter(user=self.user1, post=post).exists())

    def test_media_size_validators(self):
        # Verify 10MB image validator triggers
        large_image = SimpleUploadedFile(
            name="large_image.jpg",
            content=b"0" * (10 * 1024 * 1024 + 100),
            content_type="image/jpeg"
        )
        post = Post(author=self.user1, content="Image post", image=large_image, post_type='TEXT')
        with self.assertRaises(ValidationError):
            post.full_clean()

        # Verify 30MB video validator triggers
        large_video = SimpleUploadedFile(
            name="large_video.mp4",
            content=b"0" * (30 * 1024 * 1024 + 100),
            content_type="video/mp4"
        )
        post2 = Post(author=self.user1, content="Video post", video=large_video, post_type='TEXT')
        with self.assertRaises(ValidationError):
            post2.full_clean()
