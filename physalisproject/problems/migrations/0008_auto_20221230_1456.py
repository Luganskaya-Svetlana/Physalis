# Generated by Django 3.2.4 on 2022-12-30 11:56

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0007_auto_20221230_1423'),
    ]

    operations = [
        migrations.AlterField(
            model_name='problem',
            name='answer',
            field=models.CharField(blank=True, help_text='Максимум 50 символов', max_length=50, null=True, verbose_name='ответ'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='problems', to='problems.category', verbose_name='категория'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='complexity',
            field=models.PositiveSmallIntegerField(blank=True, help_text='число от 1 до 10 включительно', null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(10)], verbose_name='сложность'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='solution',
            field=models.TextField(blank=True, help_text='Максимум 6 тыс. символов', max_length=6000, null=True, verbose_name='решение'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='tags',
            field=models.ManyToManyField(blank=True, related_name='problems', to='problems.Tag', verbose_name='тэги'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='type_ege',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='problems', to='problems.typeinege', verbose_name='Тип задания'),
        ),
    ]
