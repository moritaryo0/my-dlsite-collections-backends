from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserList


@receiver(post_save, sender=get_user_model())
def create_home_list_on_user_create(sender, instance, created, **kwargs):
    if created:
        UserList.objects.get_or_create(
            owner=instance,
            name='Home',
            defaults={'description': 'ホーム', 'is_public': True}
        )

