from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_userprofile_admin_users_seen_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='telegram_login',
            field=models.CharField(blank=True, max_length=64, verbose_name='логин в Telegram'),
        ),
    ]
