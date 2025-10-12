from django.db import models

# Create your models here.
class UserPost(models.Model):
    user_id = models.CharField(max_length=200)
    description = models.TextField(max_length=1000, blank=True, null=True)
    content_url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    good_count = models.IntegerField(default=0)

    def __str__(self):
        return self.user_id

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
    user_id = models.CharField(max_length=200)
    content_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user_id', 'content_url')

    def __str__(self):
        return f"{self.user_id} liked {self.content_url}"