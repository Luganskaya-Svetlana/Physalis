# Generated by Django 3.2.4 on 2023-04-26 14:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('variants', '0011_alter_variant_problems'),
    ]

    operations = [
        migrations.AddField(
            model_name='variant',
            name='is_published',
            field=models.BooleanField(default=True, verbose_name='показывать в списке вариантов'),
        ),
    ]