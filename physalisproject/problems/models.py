from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Tag(models.Model):
    '''Модель тегов'''
    name = models.CharField('название',
                            max_length=150,
                            help_text='Максимум 150 символов')
    slug = models.SlugField('слаг',
                            max_length=150,
                            help_text=('Слаг - текстовый идентификатор,'
                                       ' с помощью которого будут'
                                       ' генерироваться ссылки'))

    class Meta:
        verbose_name = 'тэг'
        verbose_name_plural = 'тэги'
        default_related_name = 'tags'

    def __str__(self):
        return self.name


class Source(models.Model):
    '''Модель источников'''
    name = models.CharField('название',
                            max_length=500,
                            help_text='Максимум 500 символов')

    class Meta:
        verbose_name = 'источник'
        verbose_name_plural = 'источники'
        default_related_name = 'source'

    def __str__(self):
        return self.name


class Category(models.Model):
    '''Модель категорий (разделов и подразделов)'''
    name = models.CharField('название',
                            max_length=150,
                            help_text='Максимум 150 символов')
    slug = models.SlugField('слаг',
                            max_length=150,
                            help_text=('Слаг - текстовый идентификатор,'
                                       ' с помощью которого будут'
                                       ' генерироваться ссылки'))
    parent = models.ForeignKey('Category',
                               default=None,
                               on_delete=models.CASCADE,
                               blank=True,
                               null=True,
                               verbose_name=('Название раздела'
                                             ' (только для подразделов)'))

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'
        default_related_name = 'category'

    def __str__(self):
        return self.name


class PartOfEGE(models.Model):
    '''Модель частей ЕГЭ'''
    name = models.CharField('название',
                            max_length=150,
                            help_text='Максимум 150 символов')

    class Meta:
        verbose_name = 'часть'
        verbose_name_plural = 'части'
        default_related_name = 'part'

    def __str__(self):
        return self.name


class TypeInEGE(models.Model):
    '''Модель типов заданий в ЕГЭ'''
    number = models.PositiveSmallIntegerField('номер')
    max_score = models.PositiveSmallIntegerField('максимальное количество'
                                                 ' баллов')
    part_ege = models.ForeignKey(PartOfEGE,
                                 on_delete=models.CASCADE,
                                 verbose_name='часть ЕГЭ',
                                 default=1)

    class Meta:
        verbose_name = 'тип'
        verbose_name_plural = 'типы'
        default_related_name = 'type'

    def __str__(self):
        return str(self.number)


class Problem(models.Model):
    '''Модель задач'''
    text = models.TextField('условие',
                            max_length=6000,
                            help_text='Максимум 6 тыс. символов '
                            '(если мало - обратитесь к создательнице сайта)')
    solution = models.TextField('решение',
                                max_length=6000,
                                help_text='Максимум 6 тыс. символов',
                                blank=True,
                                null=True)
    answer = models.CharField('ответ',
                              max_length=50,
                              help_text='Максимум 50 символов',
                              blank=True,
                              null=True)
    complexity = models.PositiveSmallIntegerField('сложность',
                                                  help_text=('число от 1 до 10'
                                                             ' включительно'),
                                                  blank=True,
                                                  null=True,
                                                  validators=(
                                                      [MinValueValidator(1),
                                                       MaxValueValidator(10)]))
    author = models.ForeignKey(User,
                               on_delete=models.CASCADE,
                               editable=False,
                               verbose_name='автор')
    date = models.DateField('дата добавления',
                            auto_now_add=True)
    tags = models.ManyToManyField(Tag,
                                  verbose_name='тэги',
                                  blank=True)
    source = models.ForeignKey(Source,
                               on_delete=models.CASCADE,
                               verbose_name='источник',
                               blank=True,
                               null=True)
    category = models.ForeignKey(Category,
                                 on_delete=models.CASCADE,
                                 verbose_name='категория',
                                 blank=True,
                                 null=True)
    type_ege = models.ForeignKey(TypeInEGE,
                                 on_delete=models.CASCADE,
                                 verbose_name='Тип задания',
                                 blank=True,
                                 null=True)

    class Meta:
        verbose_name = 'задача'
        verbose_name_plural = 'задачи'
        default_related_name = 'problems'

    def __str__(self):
        return f'задача с id {self.id}'
