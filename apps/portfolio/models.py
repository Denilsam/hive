from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from apps.profiles.models import validate_image_size, Skill


class Project(models.Model):
    class Category(models.TextChoices):
        WEB_DEVELOPMENT = 'WEB_DEVELOPMENT', 'Web Development'
        MOBILE_APP = 'MOBILE_APP', 'Mobile App'
        AI_ML = 'AI_ML', 'AI & Machine Learning'
        DESIGN = 'DESIGN', 'UI/UX Design'
        ROBOTICS = 'ROBOTICS', 'Robotics'
        OTHER = 'OTHER', 'Other'

    class Visibility(models.TextChoices):
        PUBLIC = 'PUBLIC', 'Public'
        CONNECTIONS = 'CONNECTIONS', 'Connections'
        PRIVATE = 'PRIVATE', 'Private'

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='projects'
    )
    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    project_image = models.ImageField(
        upload_to='projects/images/',
        validators=[validate_image_size],
        blank=True,
        null=True
    )
    short_description = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(
        max_length=30,
        choices=Category.choices,
        default=Category.OTHER
    )
    technologies = models.ManyToManyField(Skill, related_name='projects')
    
    github_url = models.URLField(blank=True, null=True)
    demo_url = models.URLField(blank=True, null=True)
    video_url = models.URLField(blank=True, null=True)
    
    start_date = models.DateField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def youtube_embed_url(self):
        if not self.video_url:
            return None
        import re
        url = self.video_url.strip()
        # Handle standard watch URLs, short URLs (youtu.be), or embed URLs
        youtube_regex = (
            r'(?:https?:\/\/)?(?:www\.)?'
            r'(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)'
            r'([a-zA-Z0-9_-]{11})'
        )
        match = re.search(youtube_regex, url)
        if match:
            video_id = match.group(1)
            return f"https://www.youtube.com/embed/{video_id}"
        return None

    class Meta:
        ordering = ['-is_featured', '-created_at']

    def clean(self):
        super().clean()
        # Date validation
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("Start date cannot be after end date.")
        
        # Featured project limit: exactly 3
        if self.is_featured:
            featured_count = Project.objects.filter(
                owner=self.owner,
                is_featured=True
            ).exclude(pk=self.pk).count()
            if featured_count >= 3:
                raise ValidationError("You can only feature up to 3 projects.")

    def save(self, *args, **kwargs):
        # Auto slugify title if empty
        if not self.slug:
            base_slug = slugify(self.title)
            slug = base_slug
            counter = 1
            while Project.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} by {self.owner.email}"


class ProjectImage(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(
        upload_to='projects/gallery/',
        validators=[validate_image_size]
    )
    caption = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.project.title} ({self.id})"


class ProjectLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_likes'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'project')

    def __str__(self):
        return f"{self.user.email} liked project {self.project.title}"


class ProjectComment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_comments'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.email} on project {self.project.title}"


class Certificate(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='portfolio_certificates'
    )
    title = models.CharField(max_length=150)
    organization = models.CharField(max_length=150)
    issue_date = models.DateField()
    certificate_url = models.URLField(blank=True, null=True)
    certificate_file = models.FileField(
        upload_to='certificates/',
        validators=[validate_image_size],
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} from {self.organization} ({self.user.email})"


class ProjectView(models.Model):
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='views'
    )
    visitor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='project_views'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        visitor_email = self.visitor.email if self.visitor else "Anonymous"
        return f"View of {self.project.title} by {visitor_email} at {self.created_at}"
