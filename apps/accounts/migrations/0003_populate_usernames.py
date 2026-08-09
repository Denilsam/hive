from django.db import migrations

def populate_missing_usernames(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    for user in User.objects.filter(username__isnull=True) | User.objects.filter(username=''):
        if user.email:
            base_username = user.email.split('@')[0]
        else:
            base_username = f"user_{user.pk}"
        
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exclude(pk=user.pk).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        user.username = username
        user.save(update_fields=['username'])

def reverse_func(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_user_managers_alter_user_account_type_and_more'),
    ]

    operations = [
        migrations.RunPython(populate_missing_usernames, reverse_func),
    ]
