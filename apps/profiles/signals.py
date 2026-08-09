from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Signal handler to automatically create a Profile instance
    when a new normal User is created. Superusers do not receive a Connect Profile.
    """
    if created and not instance.is_superuser:
        Profile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Signal handler to ensure user profile is saved on User update.
    Superusers do not have a Connect Profile.
    """
    if instance.is_superuser:
        return
    if hasattr(instance, 'profile') and instance.profile is not None:
        instance.profile.save()
    elif not instance.is_superuser:
        profile, created = Profile.objects.get_or_create(user=instance)
        profile.save()
