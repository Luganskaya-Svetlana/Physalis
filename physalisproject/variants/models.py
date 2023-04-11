from django.db import models
from django.urls import reverse
from problems.models import Problem
from variants.managers import VariantManager

from .validators import validate_answer_slug


class Variant(models.Model):
    objects = VariantManager()

    problems = models.ManyToManyField(Problem,
                                      verbose_name='задачи')
    text = models.TextField('комментарии', blank=True, null=True)
    complexity = models.FloatField('сложность', blank=True, default=0)
    is_full = models.BooleanField('полный вариант', default=True)
    show_answers = models.BooleanField('показать решения', default=True)
    date = models.DateField('дата добавления', auto_now_add=True)
    answer_slug = models.SlugField('slug для получения ответов',
                                   max_length=4, unique=False,
                                   blank=True, default='foxy',
                                   validators=[validate_answer_slug])

    class Meta:
        verbose_name = 'вариант'
        verbose_name_plural = 'варианты'
        default_related_name = 'variants'

    def get_problems(self):
        return (self.problems
                    .order_by('type_ege__number')
                    .only('text', 'type_ege__number'))

    def get_answers(self):
        return (self.problems
                    .order_by('type_ege__number')
                    .only('solution', 'answer', 'type_ege__max_score'))

    def __str__(self):
        return f'вариант с id {self.id}'

    def get_absolute_url(self):
        return reverse('variants:detail', kwargs={'pk': self.pk})

    def get_answers_url(self):
        return reverse('variants:answers', kwargs={'pk': self.pk,
                                                   'slug': self.answer_slug})
