from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Tag(models.Model):
    name = models.CharField('название',
                            max_length=150,
                            help_text='Максимум 150 символов')
    slug = models.SlugField('слаг',
                            max_length=150,
                            help_text=('Слаг - текстовый идентификатор,'
                                       'с помощью которого будут'
                                       'генерироваться ссылки)'))

    class Meta:
        verbose_name = 'тэг'
        verbose_name_plural = 'тэги'
        default_related_name = 'tags'

    def __str__(self):
        return self.name


class Source(models.Model):
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
    name = models.CharField('название',
                            max_length=150,
                            help_text='Максимум 150 символов')
    slug = models.SlugField('слаг',
                            max_length=150,
                            help_text=('Слаг - текстовый идентификатор,'
                                       'с помощью которого будут'
                                       'генерироваться ссылки)'))

    class Meta:
        verbose_name = 'категория'
        verbose_name_plural = 'категории'
        default_related_name = 'category'

    def __str__(self):
        return self.name


class PartOfEGE(models.Model):
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
    number = models.PositiveSmallIntegerField('номер')
    max_score = models.PositiveSmallIntegerField('максимальное количество'
                                                 'баллов')

    class Meta:
        verbose_name = 'тип'
        verbose_name_plural = 'типы'
        default_related_name = 'type'

    def __str__(self):
        return self.number


class Problem(models.Model):
    text = models.TextField('условие',
                            max_length=6000,
                            help_text='Максимум 6 тыс. символов'
                            '(если мало - обратитесь к создательнице сайта)')
    solution = models.TextField('решение',
                                max_length=6000,
                                help_text='Максимум 6 тыс. символов')
    answer = models.CharField('ответ',
                              max_length=50,
                              help_text='Максимум 50 символов')
    complexity = models.IntegerField('сложность',
                                     help_text='число от 1 до 10 включительно',
                                     validators=(
                                        [MinValueValidator(1),
                                         MaxValueValidator(10)]))
    author = models.ForeignKey(User,
                               on_delete=models.CASCADE,
                               editable=False)
    date = models.DateField('дата добавления',
                            auto_now_add=True)
    tags = models.ManyToManyField(Tag,
                                  verbose_name='тэги')
    source = models.ForeignKey(Source,
                               on_delete=models.CASCADE,
                               verbose_name='источник')
    category = models.ForeignKey(Category,
                                 on_delete=models.CASCADE,
                                 verbose_name='категория')
    part_ege = models.ForeignKey(PartOfEGE,
                                 on_delete=models.CASCADE,
                                 verbose_name='часть ЕГЭ')
    type_ege = models.ForeignKey(TypeInEGE,
                                 on_delete=models.CASCADE,
                                 verbose_name='Тип задания')

    class Meta:
        verbose_name = 'задача'
        verbose_name_plural = 'задачи'
        default_related_name = 'problems'

    def __str__(self):
        return f'задача с id {self.id}'
