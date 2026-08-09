from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


def validate_post_image(value):
    """
    Validates that post images are under 10MB.
    """
    if value.size > 10 * 1024 * 1024:
        raise ValidationError("Maximum image size allowed is 10MB.")
    return value


def validate_post_video(value):
    """
    Validates that post videos are under 30MB.
    """
    if value.size > 30 * 1024 * 1024:
        raise ValidationError("Maximum video size allowed is 30MB.")
    return value


class Post(models.Model):
    class PostType(models.TextChoices):
        TEXT = 'TEXT', 'Text'
        IMAGE = 'IMAGE', 'Image'
        VIDEO = 'VIDEO', 'Video'
        PROJECT_UPDATE = 'PROJECT_UPDATE', 'Project Update'
        ACHIEVEMENT = 'ACHIEVEMENT', 'Achievement'

    class Visibility(models.TextChoices):
        PUBLIC = 'PUBLIC', 'Public'
        CONNECTIONS = 'CONNECTIONS', 'Connections'
        PRIVATE = 'PRIVATE', 'Private'

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='posts'
    )
    content = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to='posts/images/',
        validators=[validate_post_image],
        blank=True,
        null=True
    )
    video = models.FileField(
        upload_to='posts/videos/',
        validators=[validate_post_video],
        blank=True,
        null=True
    )
    post_type = models.CharField(
        max_length=20,
        choices=PostType.choices,
        default=PostType.TEXT
    )
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        if not self.content and not self.image and not self.video:
            raise ValidationError("A post must contain either text content or media (image/video).")

    def __str__(self):
        return f"Post by {self.author.email} ({self.post_type}) at {self.created_at}"


class Like(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='likes'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.email} liked post {self.post.id}"


class Comment(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment by {self.user.email} on post {self.post.id}"


class SavedPost(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_posts'
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='saved_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')

    def __str__(self):
        return f"{self.user.email} saved post {self.post.id}"
