# Generated by Django 3.2.4 on 2023-03-20 17:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('variants', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='variant',
            name='show_answers',
            field=models.BooleanField(default=True, verbose_name='показать решения'),
        ),
    ]
