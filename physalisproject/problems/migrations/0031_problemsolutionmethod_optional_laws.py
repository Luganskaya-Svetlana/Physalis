from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0030_cleanup_reference_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='problemsolutionmethod',
            name='optional_laws',
            field=models.ManyToManyField(
                blank=True,
                related_name='optional_in_solution_methods',
                to='problems.Law',
                verbose_name='необязательные законы',
            ),
        ),
    ]
