from django.db import migrations, models


JUNK_PART_NAMES = ('P', 'Р', 'Часть 1', 'Часть 2')
JUNK_SOURCE_NAMES = ('S', 'Источник 2')
JUNK_PROBLEM_IDS = (1673, 1674, 1675, 1676, 1677, 1678)


def deduplicate_types(apps, schema_editor):
    Problem = apps.get_model('problems', 'Problem')
    TypeInEGE = apps.get_model('problems', 'TypeInEGE')
    db_alias = schema_editor.connection.alias

    canonical_ids = {}
    duplicates = []
    for type_ege in TypeInEGE.objects.using(db_alias).order_by('id'):
        key = (type_ege.part_ege_id, type_ege.number)
        canonical_id = canonical_ids.get(key)
        if canonical_id is None:
            canonical_ids[key] = type_ege.id
            continue

        Problem.objects.using(db_alias).filter(type_ege_id=type_ege.id).update(
            type_ege_id=canonical_id
        )
        duplicates.append(type_ege.id)

    if duplicates:
        TypeInEGE.objects.using(db_alias).filter(id__in=duplicates).delete()


def cleanup_reference_data(apps, schema_editor):
    Problem = apps.get_model('problems', 'Problem')
    Source = apps.get_model('problems', 'Source')
    PartOfEGE = apps.get_model('problems', 'PartOfEGE')
    TypeInEGE = apps.get_model('problems', 'TypeInEGE')
    db_alias = schema_editor.connection.alias

    generic_part, _ = PartOfEGE.objects.using(db_alias).get_or_create(
        name='Не входит в ЕГЭ этого года'
    )

    for old_part in PartOfEGE.objects.using(db_alias).filter(
        name='Не входит в ЕГЭ-2024'
    ).exclude(pk=generic_part.pk):
        TypeInEGE.objects.using(db_alias).filter(part_ege_id=old_part.pk).update(
            part_ege_id=generic_part.pk
        )
        old_part.delete()

    deduplicate_types(apps, schema_editor)

    Problem.objects.using(db_alias).filter(id__in=JUNK_PROBLEM_IDS).delete()
    TypeInEGE.objects.using(db_alias).filter(part_ege__name__in=JUNK_PART_NAMES).delete()

    for source_name in JUNK_SOURCE_NAMES:
        for source in Source.objects.using(db_alias).filter(name=source_name):
            if not Problem.objects.using(db_alias).filter(source_id=source.pk).exists():
                source.delete()

    PartOfEGE.objects.using(db_alias).filter(name__in=JUNK_PART_NAMES).delete()
    deduplicate_types(apps, schema_editor)


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0029_auto_20260406_0534'),
    ]

    operations = [
        migrations.RunPython(cleanup_reference_data, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='partofege',
            name='name',
            field=models.CharField(
                help_text='Максимум 150 символов',
                max_length=150,
                unique=True,
                verbose_name='название',
            ),
        ),
        migrations.AlterField(
            model_name='source',
            name='name',
            field=models.CharField(
                help_text='Максимум 500 символов',
                max_length=500,
                unique=True,
                verbose_name='название',
            ),
        ),
        migrations.AddConstraint(
            model_name='typeinege',
            constraint=models.UniqueConstraint(
                fields=('number', 'part_ege'),
                name='unique_typeinege_number_per_part',
            ),
        ),
    ]
