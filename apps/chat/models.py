from django.db import models, IntegrityError
from django.conf import settings
from django.core.exceptions import ValidationError


class Conversation(models.Model):
    user1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_user1'
    )
    user2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='conversations_as_user2'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        # We will enforce user1 < user2 at database/model level to avoid user1, user2 and user2, user1 duplicates
        unique_together = ('user1', 'user2')

    def clean(self):
        super().clean()
        if self.user1 == self.user2:
            raise ValidationError("You cannot create a conversation with yourself.")
        
        # Enforce ordering to prevent user1=A, user2=B and user1=B, user2=A duplicates
        if self.user1_id and self.user2_id:
            if self.user1_id > self.user2_id:
                # Swap them
                self.user1, self.user2 = self.user2, self.user1

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @classmethod
    def get_or_create_conversation(cls, user_a, user_b):
        if user_a.id == user_b.id:
            raise ValidationError("You cannot create a conversation with yourself.")
        
        u1, u2 = (user_a, user_b) if user_a.id < user_b.id else (user_b, user_a)
        try:
            return cls.objects.get_or_create(user1=u1, user2=u2)
        except IntegrityError:
            return cls.objects.get(user1=u1, user2=u2), False

    def get_other_user(self, user):
        if user == self.user1:
            return self.user2
        elif user == self.user2:
            return self.user1
        return None

    def __str__(self):
        return f"Chat between {self.user1.email} and {self.user2.email}"


class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    content = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def clean(self):
        super().clean()
        if self.sender != self.conversation.user1 and self.sender != self.conversation.user2:
            raise ValidationError("Sender must be a participant of the conversation.")

    def save(self, *args, **kwargs):
        self.full_clean()
        # Update updated_at of conversation
        super().save(*args, **kwargs)
        self.conversation.save() # Triggers auto_now update for updated_at

    def __str__(self):
        return f"Message from {self.sender.email} at {self.created_at}"
