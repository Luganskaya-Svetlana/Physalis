# Generated by Django 3.2.4 on 2022-12-30 12:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0008_auto_20221230_1456'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='typeinege',
            options={'default_related_name': 'type', 'ordering': ['number'], 'verbose_name': 'тип', 'verbose_name_plural': 'типы'},
        ),
    ]
