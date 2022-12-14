# Generated by Django 3.2.4 on 2022-12-24 19:24

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0002_alter_problem_complexity'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='parent',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='category', to='problems.category'),
        ),
        migrations.AlterField(
            model_name='category',
            name='slug',
            field=models.SlugField(help_text='Слаг - текстовый идентификатор, с помощью которого будут генерироваться ссылки)', max_length=150, verbose_name='слаг'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='complexity',
            field=models.PositiveSmallIntegerField(help_text='число от 1 до 10 включительно', validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(10)], verbose_name='сложность'),
        ),
        migrations.AlterField(
            model_name='problem',
            name='text',
            field=models.TextField(help_text='Максимум 6 тыс. символов (если мало - обратитесь к создательнице сайта)', max_length=6000, verbose_name='условие'),
        ),
        migrations.AlterField(
            model_name='tag',
            name='slug',
            field=models.SlugField(help_text='Слаг - текстовый идентификатор, с помощью которого будут генерироваться ссылки)', max_length=150, verbose_name='слаг'),
        ),
        migrations.AlterField(
            model_name='typeinege',
            name='max_score',
            field=models.PositiveSmallIntegerField(verbose_name='максимальное количество баллов'),
        ),
    ]
