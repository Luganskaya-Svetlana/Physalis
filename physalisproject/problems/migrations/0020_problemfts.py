# Generated by Django 3.2.4 on 2023-05-10 20:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0019_auto_20230308_1253'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProblemFTS',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField()),
            ],
            options={
                'db_table': 'problems_problem_fts',
                'managed': False,
            },
        ),
    ]
