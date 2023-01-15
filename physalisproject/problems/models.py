from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.safestring import mark_safe
from django_cleanup.signals import cleanup_pre_delete
from sorl.thumbnail import delete, get_thumbnail
from django.templatetags.static import static


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


class CategoryBaseModel(models.Model):
    '''Базовый класс для категорий и подкатегорий,
       чтобы снизить количество копипаста'''
    name = models.CharField('название',
                            max_length=150,
                            help_text='Максимум 150 символов')
    slug = models.SlugField('слаг',
                            max_length=150,
                            help_text=('Слаг - текстовый идентификатор,'
                                       ' с помощью которого будут'
                                       ' генерироваться ссылки'))

    class Meta:
        abstract = True

    def __str__(self):
        return self.name


class Category(CategoryBaseModel):
    '''Модель категорий (разделов)'''

    class Meta:
        verbose_name = 'раздел'
        verbose_name_plural = 'разделы'
        default_related_name = 'category'


class Subcategory(CategoryBaseModel):
    '''Модель подкатегорий (подразделов)'''

    class Meta:
        verbose_name = 'подраздел'
        verbose_name_plural = 'подразделы'
        default_related_name = 'subcategory'


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
        ordering = ['number']

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
    answer = models.TextField('ответ',
                              max_length=1000,
                              help_text='Максимум 1 тыс. символов',
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
                                 verbose_name='раздел',
                                 blank=True,
                                 null=True)
    subcategory = models.ForeignKey(Subcategory,
                                    on_delete=models.CASCADE,
                                    verbose_name='подраздел',
                                    blank=True,
                                    null=True)
    type_ege = models.ForeignKey(TypeInEGE,
                                 on_delete=models.CASCADE,
                                 verbose_name='Тип задания',
                                 null=True)

    class Meta:
        verbose_name = 'задача'
        verbose_name_plural = 'задачи'
        default_related_name = 'problems'

    def __str__(self):
        return f'задача с id {self.id}'

    def get_absolute_url(self):
        return reverse('problems:detail', kwargs={'pk': self.pk})


class Image(models.Model):
    RELATIONS = [
        (1, 'условию'),
        (2, 'решению'),
        (3, 'ответу')
    ]
    path_to_image = models.ImageField('изображение',
                                      upload_to='media/%Y/%m',
                                      default='')
    problem = models.ForeignKey(Problem,
                                verbose_name='задача',
                                on_delete=models.CASCADE)
    relation = models.PositiveSmallIntegerField('относится к',
                                                choices=RELATIONS)

    @property
    def get_img(self):
        return get_thumbnail(self.path_to_image, '300x300', crop='center',
                             quality=51)

    def sorl_delete(**kwargs):
        delete(kwargs['file'])

    cleanup_pre_delete.connect(sorl_delete)

    class Meta:
        verbose_name = 'изображение'
        verbose_name_plural = 'изображения'
        default_related_name = 'image'

    def image_tmb(self):
        if self.path_to_image.url[-3:] == 'svg':
            url = static('img/tmb_for_svg.png')
            return mark_safe(
                f'<img src="{url}">'
            )
        if self.path_to_image:
            return mark_safe(
                f'<img src="{self.get_img.url}">'
            )
        return 'Нет изображения'

    image_tmb.short_description = 'изображение'
    image_tmb.allow_tags = True

    def __str__(self):
        return (f'одно из изображений для {self.problem}')
