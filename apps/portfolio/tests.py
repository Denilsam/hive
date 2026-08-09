from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
import json
import datetime

from apps.portfolio.models import Project, ProjectImage, ProjectLike, ProjectComment
from apps.profiles.models import Skill
from apps.posts.models import Post

User = get_user_model()


class PortfolioSystemTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create users
        self.user1 = User.objects.create_user(
            email='owner@example.com',
            password='StrongPassword123!',
            first_name='Owner',
            last_name='User',
            account_type='FREELANCER',
            is_verified=True,
            is_active=True
        )
        self.user2 = User.objects.create_user(
            email='viewer@example.com',
            password='StrongPassword123!',
            first_name='Viewer',
            last_name='User',
            account_type='STUDENT',
            is_verified=True,
            is_active=True
        )
        
        self.create_url = reverse('portfolio:project_create')
        self.explore_url = reverse('portfolio:portfolio_explore')

    def test_project_creation_authenticated(self):
        self.client.login(email='owner@example.com', password='StrongPassword123!')
        
        response = self.client.post(self.create_url, {
            'title': 'Test Project',
            'category': 'WEB_DEVELOPMENT',
            'short_description': 'A test project summary',
            'description': 'A detailed explanation of the project',
            'tech_tags': 'Django, Python, HTML',
            'start_date': '2025-01-01',
            'end_date': '2025-06-01',
            'is_featured': False,
            'visibility': 'PUBLIC',
            'demo_url': 'https://demo.example.com'
        })
        self.assertEqual(response.status_code, 302)  # Redirects to portfolio detail page
        
        # Verify in DB
        project = Project.objects.first()
        self.assertIsNotNone(project)
        self.assertEqual(project.owner, self.user1)
        self.assertEqual(project.title, 'Test Project')
        self.assertEqual(project.slug, 'test-project')
        
        # Verify tech tags mapping
        tech_names = list(project.technologies.values_list('name', flat=True))
        self.assertIn('Django', tech_names)
        self.assertIn('Python', tech_names)
        
        # Verify feed post creation is decoupled (no feed post created)
        feed_post = Post.objects.first()
        self.assertIsNone(feed_post)

    def test_featured_project_limit_validation(self):
        # Create 3 featured projects for user1
        for i in range(3):
            Project.objects.create(
                owner=self.user1,
                title=f"Featured {i}",
                short_description="Featured project",
                description="Details",
                category="WEB_DEVELOPMENT",
                start_date=datetime.date(2025, 1, 1),
                is_featured=True
            )
            
        # Try to create a 4th featured project
        proj = Project(
            owner=self.user1,
            title="Featured 4",
            short_description="Should fail",
            description="Details",
            category="WEB_DEVELOPMENT",
            start_date=datetime.date(2025, 1, 1),
            is_featured=True
        )
        with self.assertRaises(ValidationError):
            proj.full_clean()

    def test_project_permissions_edit_unauthorized_blocked(self):
        project = Project.objects.create(
            owner=self.user1,
            title="Owner Project",
            short_description="Owner project",
            description="Details",
            category="WEB_DEVELOPMENT",
            start_date=datetime.date(2025, 1, 1)
        )
        
        # Log in as user2 (viewer)
        self.client.login(email='viewer@example.com', password='StrongPassword123!')
        edit_url = reverse('portfolio:project_edit', kwargs={'pk': project.pk})
        
        # Try fetching edit view (should return 404 since owner filter blocks it)
        response = self.client.get(edit_url)
        self.assertEqual(response.status_code, 404)

    def test_project_like_toggle_ajax(self):
        self.client.login(email='viewer@example.com', password='StrongPassword123!')
        project = Project.objects.create(
            owner=self.user1,
            title="Like Project",
            short_description="Like project",
            description="Details",
            category="WEB_DEVELOPMENT",
            start_date=datetime.date(2025, 1, 1)
        )
        like_url = reverse('portfolio:project_like_toggle', kwargs={'pk': project.pk})
        
        # Like
        response = self.client.post(like_url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['liked'])
        self.assertEqual(data['likes_count'], 1)
        
        # Unlike
        response = self.client.post(like_url)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['liked'])
        self.assertEqual(data['likes_count'], 0)

    def test_project_comment_ajax(self):
        self.client.login(email='viewer@example.com', password='StrongPassword123!')
        project = Project.objects.create(
            owner=self.user1,
            title="Comment Project",
            short_description="Comment project",
            description="Details",
            category="WEB_DEVELOPMENT",
            start_date=datetime.date(2025, 1, 1)
        )
        comment_url = reverse('portfolio:project_comment_create', kwargs={'pk': project.pk})
        
        # Post comment
        response = self.client.post(comment_url, {'content': 'Cool project!'})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['comment']['content'], 'Cool project!')
        
        comment_id = data['comment']['id']
        
        # Delete comment
        delete_url = reverse('portfolio:project_comment_delete', kwargs={'pk': comment_id})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(ProjectComment.objects.filter(pk=comment_id).exists())

    def test_search_and_filters(self):
        p1 = Project.objects.create(
            owner=self.user1,
            title="React Native App",
            short_description="Mobile project",
            description="Details",
            category="MOBILE_APP",
            start_date=datetime.date(2025, 1, 1)
        )
        p1.technologies.add(Skill.objects.create(name="React Native"))
        
        p2 = Project.objects.create(
            owner=self.user1,
            title="Django Web App",
            short_description="Web project",
            description="Details",
            category="WEB_DEVELOPMENT",
            start_date=datetime.date(2025, 1, 1)
        )
        p2.technologies.add(Skill.objects.create(name="Django"))
        
        # Search for "Django"
        response = self.client.get(self.explore_url, {'q': 'Django'})
        self.assertEqual(response.status_code, 200)
        projects = list(response.context['projects'])
        self.assertIn(p2, projects)
        self.assertNotIn(p1, projects)

        # Filter by Category MOBILE_APP
        response2 = self.client.get(self.explore_url, {'category': 'MOBILE_APP'})
        self.assertEqual(response2.status_code, 200)
        projects2 = list(response2.context['projects'])
        self.assertIn(p1, projects2)
        self.assertNotIn(p2, projects2)

    def test_project_visibility_controls(self):
        # 1. Private project
        private_project = Project.objects.create(
            owner=self.user1,
            title="Private project",
            short_description="Owner project",
            description="Details",
            category="WEB_DEVELOPMENT",
            start_date=datetime.date(2025, 1, 1),
            visibility='PRIVATE'
        )
        
        # 2. Connections project
        connections_project = Project.objects.create(
            owner=self.user1,
            title="Connections project",
            short_description="Owner project",
            description="Details",
            category="WEB_DEVELOPMENT",
            start_date=datetime.date(2025, 1, 1),
            visibility='CONNECTIONS'
        )

        # 3. Public project
        public_project = Project.objects.create(
            owner=self.user1,
            title="Public project",
            short_description="Owner project",
            description="Details",
            category="WEB_DEVELOPMENT",
            start_date=datetime.date(2025, 1, 1),
            visibility='PUBLIC'
        )

        detail_url_private = reverse('portfolio:project_detail', kwargs={'slug': private_project.slug})
        detail_url_conn = reverse('portfolio:project_detail', kwargs={'slug': connections_project.slug})
        detail_url_pub = reverse('portfolio:project_detail', kwargs={'slug': public_project.slug})

        # Test anonymous user
        self.client.logout()
        response = self.client.get(detail_url_private)
        self.assertEqual(response.status_code, 404)
        
        response = self.client.get(detail_url_conn)
        self.assertEqual(response.status_code, 404)
        
        response = self.client.get(detail_url_pub)
        self.assertEqual(response.status_code, 200)

        # Test non-connected user2
        self.client.login(email='viewer@example.com', password='StrongPassword123!')
        response = self.client.get(detail_url_private)
        self.assertEqual(response.status_code, 404)
        
        response = self.client.get(detail_url_conn)
        self.assertEqual(response.status_code, 404)
        
        response = self.client.get(detail_url_pub)
        self.assertEqual(response.status_code, 200)

        # Test connected user (create connection between user1 and user2)
        from apps.connections.models import Connection
        # Order them correctly to prevent ValidationError
        u1, u2 = (self.user1, self.user2) if self.user1.id < self.user2.id else (self.user2, self.user1)
        Connection.objects.create(user1=u1, user2=u2)

        response = self.client.get(detail_url_conn)
        self.assertEqual(response.status_code, 200)

        # Owner can view private
        self.client.login(email='owner@example.com', password='StrongPassword123!')
        response = self.client.get(detail_url_private)
        self.assertEqual(response.status_code, 200)

    def test_project_view_tracking(self):
        project = Project.objects.create(
            owner=self.user1,
            title="View Project",
            short_description="Owner project",
            description="Details",
            category="WEB_DEVELOPMENT",
            start_date=datetime.date(2025, 1, 1),
            visibility='PUBLIC'
        )
        detail_url = reverse('portfolio:project_detail', kwargs={'slug': project.slug})

        # Anonymous view
        self.client.logout()
        self.client.get(detail_url)
        self.assertEqual(project.views.count(), 1)
        self.assertIsNone(project.views.first().visitor)

        # Authenticated view
        self.client.login(email='viewer@example.com', password='StrongPassword123!')
        self.client.get(detail_url)
        self.assertEqual(project.views.count(), 2)
        self.assertEqual(project.views.last().visitor, self.user2)

    def test_skill_assignment_and_duplicate_check(self):
        from apps.profiles.models import UserSkill
        skill = Skill.objects.create(name="Rust")

        # 1. Create skill assignment
        user_skill = UserSkill.objects.create(user=self.user1, skill=skill, level="EXPERT")
        self.assertEqual(user_skill.level, "EXPERT")

        # 2. Try creating duplicate assignment
        dup = UserSkill(user=self.user1, skill=skill, level="BEGINNER")
        with self.assertRaises(ValidationError):
            dup.full_clean()

    def test_certificate_upload_and_delete(self):
        self.client.login(email='owner@example.com', password='StrongPassword123!')
        
        # Test add certificate
        add_url = reverse('portfolio:certificate_add')
        response = self.client.post(add_url, {
            'title': 'AWS Certified Architect',
            'organization': 'Amazon',
            'issue_date': '2025-01-01',
            'certificate_url': 'https://credentials.com/aws-123'
        })
        self.assertEqual(response.status_code, 302)
        
        # Verify in DB
        from apps.portfolio.models import Certificate
        cert = Certificate.objects.first()
        self.assertIsNotNone(cert)
        self.assertEqual(cert.user, self.user1)
        self.assertEqual(cert.title, 'AWS Certified Architect')

        # Test delete certificate
        delete_url = reverse('portfolio:certificate_delete', kwargs={'pk': cert.id})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Certificate.objects.filter(id=cert.id).exists())

    def test_project_delete_permissions(self):
        project = Project.objects.create(
            owner=self.user1,
            title="Delete Test Project",
            short_description="To be deleted",
            description="Details",
            category="WEB_DEVELOPMENT",
            start_date=datetime.date(2025, 1, 1)
        )
        delete_url = reverse('portfolio:project_delete', kwargs={'pk': project.pk})

        # 1. Non-owner cannot delete (returns 404 due to owner filter)
        self.client.login(email='viewer@example.com', password='StrongPassword123!')
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Project.objects.filter(pk=project.pk).exists())

        # 2. GET request not allowed (returns 405 Method Not Allowed)
        self.client.login(email='owner@example.com', password='StrongPassword123!')
        response = self.client.get(delete_url)
        self.assertEqual(response.status_code, 405)

        # 3. Owner can delete via POST
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Project.objects.filter(pk=project.pk).exists())

    def test_feed_post_appears_in_portfolio_posts_single_record(self):
        self.client.login(email='owner@example.com', password='StrongPassword123!')
        
        # 1. Create post in Feed
        create_post_url = reverse('posts:create')
        response = self.client.post(create_post_url, {
            'content': 'Built a Django networking platform...',
        })
        self.assertEqual(response.status_code, 302)
        
        # 2. Verify only ONE Post record exists in database
        self.assertEqual(Post.objects.count(), 1)
        post = Post.objects.first()
        self.assertEqual(post.author, self.user1)
        self.assertEqual(post.content, 'Built a Django networking platform...')

        # 3. Verify post appears in Feed
        feed_response = self.client.get(reverse('posts:feed'))
        self.assertEqual(feed_response.status_code, 200)
        self.assertIn(post, feed_response.context['posts'])

        # 4. Verify same post appears in user's Portfolio -> Posts
        portfolio_url = reverse('portfolio:portfolio_detail', kwargs={'username': self.user1.username})
        port_response = self.client.get(portfolio_url)
        self.assertEqual(port_response.status_code, 200)
        self.assertIn(post, port_response.context['portfolio_posts'])

    def test_portfolio_posts_isolation_between_users(self):
        # User 1 creates post
        post1 = Post.objects.create(author=self.user1, content='User1 feed post')
        # User 2 creates post
        post2 = Post.objects.create(author=self.user2, content='User2 feed post')

        # View User 1's portfolio
        port_url_1 = reverse('portfolio:portfolio_detail', kwargs={'username': self.user1.username})
        resp1 = self.client.get(port_url_1)
        posts1 = list(resp1.context['portfolio_posts'])
        self.assertIn(post1, posts1)
        self.assertNotIn(post2, posts1)

        # View User 2's portfolio
        port_url_2 = reverse('portfolio:portfolio_detail', kwargs={'username': self.user2.username})
        resp2 = self.client.get(port_url_2)
        posts2 = list(resp2.context['portfolio_posts'])
        self.assertIn(post2, posts2)
        self.assertNotIn(post1, posts2)

    def test_portfolio_posts_visibility_and_security_checks(self):
        # Create public, connections, and private post for user1
        pub_post = Post.objects.create(author=self.user1, content='Public Post', visibility='PUBLIC')
        conn_post = Post.objects.create(author=self.user1, content='Connections Post', visibility='CONNECTIONS')
        priv_post = Post.objects.create(author=self.user1, content='Private Post', visibility='PRIVATE')

        port_url = reverse('portfolio:portfolio_detail', kwargs={'username': self.user1.username})

        # Owner can view all posts
        self.client.login(email='owner@example.com', password='StrongPassword123!')
        resp_owner = self.client.get(port_url)
        owner_posts = list(resp_owner.context['portfolio_posts'])
        self.assertIn(pub_post, owner_posts)
        self.assertIn(conn_post, owner_posts)
        self.assertIn(priv_post, owner_posts)

        # Non-connected viewer can only view public post
        self.client.login(email='viewer@example.com', password='StrongPassword123!')
        resp_viewer = self.client.get(port_url)
        viewer_posts = list(resp_viewer.context['portfolio_posts'])
        self.assertIn(pub_post, viewer_posts)
        self.assertNotIn(conn_post, viewer_posts)
        self.assertNotIn(priv_post, viewer_posts)

        # Viewer cannot delete user1's post (server-side check returns 404)
        delete_post_url = reverse('posts:delete', kwargs={'pk': pub_post.pk})
        del_resp = self.client.post(delete_post_url)
        self.assertEqual(del_resp.status_code, 404)
        self.assertTrue(Post.objects.filter(pk=pub_post.pk).exists())

    def test_portfolio_post_likes_comments_and_deletion(self):
        post = Post.objects.create(author=self.user1, content='Interactivity Post')

        # Viewer likes post
        self.client.login(email='viewer@example.com', password='StrongPassword123!')
        like_url = reverse('posts:like_toggle', kwargs={'pk': post.pk})
        like_resp = self.client.post(like_url)
        self.assertEqual(like_resp.status_code, 200)
        self.assertEqual(post.likes.count(), 1)

        # Viewer comments on post
        comment_url = reverse('posts:comment_create', kwargs={'pk': post.pk})
        comm_resp = self.client.post(comment_url, {'content': 'Great update!'})
        self.assertEqual(comm_resp.status_code, 200)
        self.assertEqual(post.comments.count(), 1)

        # Owner deletes post
        self.client.login(email='owner@example.com', password='StrongPassword123!')
        delete_url = reverse('posts:delete', kwargs={'pk': post.pk})
        del_resp = self.client.post(delete_url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(del_resp.status_code, 200)
        self.assertFalse(Post.objects.filter(pk=post.pk).exists())

        # Post automatically disappears from portfolio posts
        port_url = reverse('portfolio:portfolio_detail', kwargs={'username': self.user1.username})
        port_resp = self.client.get(port_url)
        self.assertNotIn(post, list(port_resp.context['portfolio_posts']))

    def test_empty_portfolio_posts_state(self):
        port_url = reverse('portfolio:portfolio_detail', kwargs={'username': self.user1.username})
        resp = self.client.get(port_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['portfolio_posts']), 0)
        self.assertContains(resp, "No posts yet")


