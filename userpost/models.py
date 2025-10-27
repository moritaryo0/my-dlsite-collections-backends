from django.db import models
from django.conf import settings
 

# Create your models here.
class UserPost(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,null=True, blank=True)
    username_legacy = models.CharField(max_length=200)
    description = models.TextField(max_length=1000, blank=True, null=True)
    content_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    good_count = models.IntegerField(default=0)
    list = models.ForeignKey('userlists.UserList', on_delete=models.SET_NULL, null=True, blank=True, related_name='userposts')

    def __str__(self):
        return self.username_legacy

class ContentData(models.Model):
    content_url = models.URLField()
    title = models.CharField(max_length=200)
    image = models.URLField()
    description = models.TextField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    content_type = models.CharField(max_length=200, default='')
    good_count = models.IntegerField(default=0)

    def __str__(self):
        return self.content_url

class Good(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,null=True, blank=True)
    username_legacy = models.CharField(max_length=200)
    content_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('username_legacy', 'content_url')

    def __str__(self):
        return f"{self.username_legacy} liked {self.content_url}"