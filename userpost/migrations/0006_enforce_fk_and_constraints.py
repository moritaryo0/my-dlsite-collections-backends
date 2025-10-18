# backend/userpost/migrations/0006_enforce_fk_and_constraints.py
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('userpost', '0005_backfill_user_fk'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userpost',
            name='user',
            field=models.ForeignKey(to='accounts.user', on_delete=django.db.models.deletion.CASCADE, related_name='posts', null=False, blank=False),
        ),
        migrations.AlterField(
            model_name='good',
            name='user',
            field=models.ForeignKey(to='accounts.user', on_delete=django.db.models.deletion.CASCADE, related_name='goods', null=False, blank=False),
        ),
        migrations.AlterUniqueTogether(
            name='good',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='good',
            constraint=models.UniqueConstraint(fields=['user', 'content_url'], name='good_user_content_unique_fk'),
        ),
    ]