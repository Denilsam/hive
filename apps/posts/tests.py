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


import io
import shutil
import tempfile
from PIL import Image
from unittest.mock import patch
from django.test import override_settings
from apps.portfolio.models import Project
from apps.profiles.models import Profile


def get_test_image(filename="test_image.png", format="PNG", size=(50, 50), color="blue"):
    file_obj = io.BytesIO()
    image = Image.new("RGB", size, color=color)
    image.save(file_obj, format=format)
    file_obj.seek(0)
    return SimpleUploadedFile(
        name=filename,
        content=file_obj.read(),
        content_type=f"image/{format.lower()}"
    )


@override_settings(MEDIA_ROOT=tempfile.gettempdir())
class MediaUploadAndStorageTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email='media_user@example.com',
            password='StrongPassword123!',
            first_name='Media',
            last_name='Tester',
            account_type='STUDENT',
            is_verified=True,
            is_active=True
        )
        self.create_url = reverse('posts:create')
        self.feed_url = reverse('posts:feed')

    def test_1_create_post_without_image(self):
        """1. Create a post without an image -> post works."""
        self.client.login(email='media_user@example.com', password='StrongPassword123!')
        response = self.client.post(self.create_url, {
            'content': 'Hello world without image!'
        })
        self.assertEqual(response.status_code, 302)
        post = Post.objects.filter(author=self.user, content='Hello world without image!').first()
        self.assertIsNotNone(post)
        self.assertFalse(bool(post.image))

        # Check feed
        feed_response = self.client.get(self.feed_url)
        self.assertEqual(feed_response.status_code, 200)
        self.assertContains(feed_response, 'Hello world without image!')

    def test_2_create_post_with_image_and_feed_display(self):
        """
        2. Create a post with an image
           -> post is created.
           -> image is uploaded.
           -> generated image URL is valid.
           -> image displays in Feed.
        """
        self.client.login(email='media_user@example.com', password='StrongPassword123!')
        img = get_test_image('post_pic.png')
        response = self.client.post(self.create_url, {
            'content': 'Post with image content',
            'image': img
        })
        self.assertEqual(response.status_code, 302)

        post = Post.objects.filter(author=self.user, content='Post with image content').first()
        self.assertIsNotNone(post)
        self.assertTrue(bool(post.image))
        self.assertTrue(post.image.url)

        # Feed displays image
        feed_response = self.client.get(self.feed_url)
        self.assertEqual(feed_response.status_code, 200)
        self.assertContains(feed_response, post.image.url)
        self.assertContains(feed_response, 'alt="Post media"')

    def test_3_refresh_page_image_still_displays(self):
        """3. Refresh the page -> image still displays."""
        self.client.login(email='media_user@example.com', password='StrongPassword123!')
        img = get_test_image('refresh_pic.png')
        self.client.post(self.create_url, {
            'content': 'Refresh post test',
            'image': img
        })
        post = Post.objects.filter(author=self.user, content='Refresh post test').first()
        self.assertIsNotNone(post)

        # First load
        feed_1 = self.client.get(self.feed_url)
        self.assertContains(feed_1, post.image.url)

        # Simulate page refresh
        feed_2 = self.client.get(self.feed_url)
        self.assertContains(feed_2, post.image.url)

    def test_4_open_post_again_detail_view(self):
        """4. Open the post again -> image still displays."""
        self.client.login(email='media_user@example.com', password='StrongPassword123!')
        img = get_test_image('detail_pic.png')
        self.client.post(self.create_url, {
            'content': 'Detail post test',
            'image': img
        })
        post = Post.objects.filter(author=self.user, content='Detail post test').first()
        self.assertIsNotNone(post)

        detail_url = reverse('posts:post_detail', kwargs={'pk': post.pk})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, post.image.url)

    def test_5_delete_post(self):
        """5. Delete the post -> post is deleted according to existing logic."""
        self.client.login(email='media_user@example.com', password='StrongPassword123!')
        img = get_test_image('delete_pic.png')
        self.client.post(self.create_url, {
            'content': 'To be deleted',
            'image': img
        })
        post = Post.objects.filter(author=self.user, content='To be deleted').first()
        self.assertIsNotNone(post)

        delete_url = reverse('posts:delete', kwargs={'pk': post.pk})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)  # Redirects to feed
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

    def test_6_profile_image_upload(self):
        """6. Profile image upload -> image displays correctly."""
        profile = self.user.profile
        profile.profile_image = get_test_image('avatar.png')
        profile.save()
        self.assertTrue(bool(profile.profile_image))
        self.assertTrue(profile.profile_image.url)
        self.assertIn('avatar', profile.profile_image.url)

    def test_7_portfolio_project_image_upload(self):
        """7. Portfolio/project image upload -> image displays correctly."""
        project = Project.objects.create(
            owner=self.user,
            title='Test Showcase Project',
            short_description='A quick description',
            description='A full detailed description of the project',
            project_image=get_test_image('project.png')
        )
        self.assertTrue(bool(project.project_image))
        self.assertTrue(project.project_image.url)
        self.assertIn('project', project.project_image.url)

    def test_8_local_development_storage_without_cloudinary_url(self):
        """8. Local development without CLOUDINARY_URL -> FileSystemStorage is used."""
        from django.core.files.storage import default_storage, FileSystemStorage
        self.assertIsInstance(default_storage, FileSystemStorage)

    def test_9_production_storage_with_cloudinary_url(self):
        """
        9. Production with CLOUDINARY_URL -> Cloudinary storage backend is configured and used.
        """
        import os
        with patch.dict(os.environ, {'CLOUDINARY_URL': 'cloudinary://123456789:abcdefgh@testhive'}):
            from cloudinary_storage.storage import MediaCloudinaryStorage
            storage = MediaCloudinaryStorage()
            fake_public_id = 'posts/images/test_mock_upload'
            generated_url = storage.url(fake_public_id)
            self.assertTrue(generated_url.startswith('https://') or generated_url.startswith('http://'))
            self.assertIn('testhive', generated_url)
            self.assertIn(fake_public_id, generated_url)

            # Test upload mock returning public id
            with patch('cloudinary.uploader.upload') as mock_upload:
                mock_upload.return_value = {'public_id': fake_public_id}
                saved_name = storage._save('test.png', io.BytesIO(b'filecontent'))
                self.assertEqual(saved_name, fake_public_id)
                self.assertEqual(storage.url(saved_name), generated_url)



