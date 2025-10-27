from django.db import models
from django.conf import settings


class UserList(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='userlists',
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    is_public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    goot_count = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['owner', 'name'], name='uniq_owner_list_name'),
        ]

    def __str__(self):
        return f"{self.owner_id}:{self.name}"


class GootList(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='list_goots',
    )
    userlist = models.ForeignKey(
        UserList,
        on_delete=models.CASCADE,
        related_name='goots',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'userlist'], name='uniq_user_list_goot'),
        ]

    def __str__(self):
        return f"{self.user_id} -> {self.userlist_id}"
