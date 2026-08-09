from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='following_relations'
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='follower_relations'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['follower', 'following'], name='unique_follow')
        ]

    def clean(self):
        if self.follower == self.following:
            raise ValidationError("You cannot follow yourself.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.follower} follows {self.following}"


class ConnectionRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        CANCELLED = 'CANCELLED', 'Cancelled'

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_requests'
    )
    receiver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_requests'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['sender', 'receiver'],
                condition=models.Q(status='PENDING'),
                name='unique_pending_request'
            )
        ]

    def clean(self):
        if self.sender == self.receiver:
            raise ValidationError("You cannot send a connection request to yourself.")

        # If they are already connected, prevent sending a request
        if Connection.objects.filter(
            models.Q(user1=self.sender, user2=self.receiver) |
            models.Q(user1=self.receiver, user2=self.sender)
        ).exists():
            raise ValidationError("You are already connected to this user.")

        # Prevent duplicate pending request in reverse direction
        if self.status == self.Status.PENDING:
            if ConnectionRequest.objects.filter(
                sender=self.receiver,
                receiver=self.sender,
                status=self.Status.PENDING
            ).exists():
                raise ValidationError("There is already a pending connection request from this user.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Request from {self.sender} to {self.receiver} ({self.status})"


class Connection(models.Model):
    user1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='connections1'
    )
    user2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='connections2'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user1', 'user2'], name='unique_connection')
        ]

    def clean(self):
        if self.user1 == self.user2:
            raise ValidationError("You cannot connect with yourself.")

    def save(self, *args, **kwargs):
        # Enforce ordering: user1_id < user2_id to prevent duplicates in reverse order
        if self.user1_id and self.user2_id and self.user1_id > self.user2_id:
            self.user1, self.user2 = self.user2, self.user1
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Connection between {self.user1} and {self.user2}"
