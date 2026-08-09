from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

# Import models dynamically/locally to avoid circular import issues
from apps.posts.models import Like, Comment
from apps.connections.models import Follow, ConnectionRequest
from apps.chat.models import Message
from apps.portfolio.models import ProjectView
from .services import create_notification


@receiver(post_save, sender=Like)
def notify_post_like(sender, instance, created, **kwargs):
    if created:
        post = instance.post
        # Prevent self-notification
        if post.author != instance.user:
            create_notification(
                receiver=post.author,
                sender=instance.user,
                notification_type='LIKE',
                message=f"{instance.user.first_name} {instance.user.last_name} liked your post.",
                related_url=reverse('posts:post_detail', kwargs={'pk': post.pk})
            )


@receiver(post_save, sender=Comment)
def notify_post_comment(sender, instance, created, **kwargs):
    if created:
        post = instance.post
        if post.author != instance.user:
            create_notification(
                receiver=post.author,
                sender=instance.user,
                notification_type='COMMENT',
                message=f"{instance.user.first_name} {instance.user.last_name} commented on your post.",
                related_url=reverse('posts:post_detail', kwargs={'pk': post.pk})
            )


@receiver(post_save, sender=Follow)
def notify_follow(sender, instance, created, **kwargs):
    if created:
        if instance.following != instance.follower:
            create_notification(
                receiver=instance.following,
                sender=instance.follower,
                notification_type='FOLLOW',
                message=f"{instance.follower.first_name} {instance.follower.last_name} started following you.",
                related_url=reverse('profiles:profile_detail', kwargs={'username': instance.follower.username})
            )


@receiver(post_save, sender=ConnectionRequest)
def notify_connection_request(sender, instance, created, **kwargs):
    if created:
        if instance.status == ConnectionRequest.Status.PENDING:
            create_notification(
                receiver=instance.receiver,
                sender=instance.sender,
                notification_type='CONNECTION_REQUEST',
                message=f"{instance.sender.first_name} {instance.sender.last_name} sent you a connection request.",
                related_url=reverse('connections:requests')
            )
    else:
        # If request is accepted
        if instance.status == ConnectionRequest.Status.ACCEPTED:
            # Check if notification already exists to prevent duplicate notifications during updates
            from .models import Notification
            exists = Notification.objects.filter(
                receiver=instance.sender,
                sender=instance.receiver,
                notification_type='CONNECTION_ACCEPTED'
            ).exists()
            if not exists:
                create_notification(
                    receiver=instance.sender,
                    sender=instance.receiver,
                    notification_type='CONNECTION_ACCEPTED',
                    message=f"{instance.receiver.first_name} {instance.receiver.last_name} accepted your connection request.",
                    related_url=reverse('profiles:profile_detail', kwargs={'username': instance.receiver.username})
                )


@receiver(post_save, sender=Message)
def notify_chat_message(sender, instance, created, **kwargs):
    if created:
        conversation = instance.conversation
        receiver_user = conversation.get_other_user(instance.sender)
        if receiver_user:
            create_notification(
                receiver=receiver_user,
                sender=instance.sender,
                notification_type='MESSAGE',
                message=f"New message from {instance.sender.first_name} {instance.sender.last_name}.",
                related_url=reverse('chat:chat_room', kwargs={'conversation_id': conversation.id})
            )


@receiver(post_save, sender=ProjectView)
def notify_portfolio_view(sender, instance, created, **kwargs):
    if created:
        project = instance.project
        # visitor can be null for anonymous views, or can be another user
        visitor = instance.visitor
        if project.owner != visitor:
            visitor_name = f"{visitor.first_name} {visitor.last_name}" if visitor else "Someone"
            create_notification(
                receiver=project.owner,
                sender=visitor,
                notification_type='PORTFOLIO_VIEW',
                message=f"{visitor_name} viewed your project '{project.title}'.",
                related_url=reverse('portfolio:portfolio_detail', kwargs={'username': project.owner.username})
            )
