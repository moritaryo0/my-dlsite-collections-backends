# backend/userpost/migrations/0005_backfill_user_fk.py
from django.db import migrations

def forwards(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    UserPost = apps.get_model('userpost', 'UserPost')
    Good = apps.get_model('userpost', 'Good')

    for up in UserPost.objects.all().iterator():
        username = getattr(up, 'username_legacy', None)
        if not username:
            continue
        try:
            u = User.objects.get(username=username)
            if up.user_id is None:  # .user_id は FKの内部ID、NULLであれば未設定
                up.user = u
                up.save(update_fields=['user'])
        except User.DoesNotExist:
            pass

    for g in Good.objects.all().iterator():
        username = getattr(g, 'username_legacy', None)
        if not username:
            continue
        try:
            u = User.objects.get(username=username)
            if g.user_id is None:
                g.user = u
                g.save(update_fields=['user'])
        except User.DoesNotExist:
            pass

def backwards(apps, schema_editor):
    UserPost = apps.get_model('userpost', 'UserPost')
    Good = apps.get_model('userpost', 'Good')
    UserPost.objects.all().update(user=None)
    Good.objects.all().update(user=None)

class Migration(migrations.Migration):

    dependencies = [
        ('userpost', '0003_rename_user_id_good_username_legacy_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]