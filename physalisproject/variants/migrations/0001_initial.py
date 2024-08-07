# Generated by Django 3.2.4 on 2023-03-20 17:10

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('problems', '0019_auto_20230308_1253'),
    ]

    operations = [
        migrations.CreateModel(
            name='Variant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(verbose_name='комментарии')),
                ('complexity', models.CharField(choices=[('Попроще', 'Попроще'), ('Нормально', 'Нормально'), ('Посложнее', 'Посложнее'), ('Дичь', 'Дичь')], max_length=100, verbose_name='сложность')),
                ('is_full', models.BooleanField(default=True, verbose_name='полный вариант')),
                ('problems', models.ManyToManyField(to='problems.Problem', verbose_name='задачи')),
            ],
        ),
    ]
