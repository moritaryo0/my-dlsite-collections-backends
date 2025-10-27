from django.db import migrations


def create_home_lists_and_assign_posts(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    UserList = apps.get_model('userlists', 'UserList')
    UserPost = apps.get_model('userpost', 'UserPost')

    for user in User.objects.all():
        home_list, _ = UserList.objects.get_or_create(owner_id=user.id, name='Home', defaults={'description': 'ホーム', 'is_public': True})
        # Assign posts for this user to Home if list is null
        UserPost.objects.filter(user_id=user.id, list__isnull=True).update(list_id=home_list.id)


class Migration(migrations.Migration):
    dependencies = [
        ('userlists', '0001_initial'),
        ('userpost', '0008_userpost_list'),
    ]

    operations = [
        migrations.RunPython(create_home_lists_and_assign_posts, migrations.RunPython.noop),
    ]

