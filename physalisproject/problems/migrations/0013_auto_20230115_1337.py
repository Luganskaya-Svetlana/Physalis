# Generated by Django 3.2.4 on 2023-01-15 10:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0012_image'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='image',
            options={'default_related_name': 'image', 'verbose_name': 'изображение', 'verbose_name_plural': 'изображения'},
        ),
        migrations.AlterField(
            model_name='image',
            name='problem',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='image', to='problems.problem', verbose_name='задача'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='answer',
            field=models.CharField(blank=True, help_text='Максимум 1 тыс. символов', max_length=1000, null=True, verbose_name='ответ'),
        ),
    ]