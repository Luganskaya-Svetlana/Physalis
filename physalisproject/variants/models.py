from django.db import models
from problems.models import Problem
from variants.managers import VariantManager


COMLEXITIES = ('Попроще', 'Нормально', 'Посложнее', 'Дичь')
CHOICES = [(elem, elem) for elem in COMLEXITIES]


class Variant(models.Model):
    objects = VariantManager()

    problems = models.ManyToManyField(Problem,
                                      verbose_name='задачи')
    text = models.TextField('комментарии', blank=True, null=True)
    complexity = models.CharField('сложность', choices=CHOICES, max_length=100)
    is_full = models.BooleanField('полный вариант', default=True)
    show_answers = models.BooleanField('показать решения', default=True)

    class Meta:
        verbose_name = 'вариант'
        verbose_name_plural = 'варианты'
        default_related_name = 'variants'

    def get_problems(self):
        return [
            pv.problem for pv in self.problems.through.objects
                                     .filter(variant_id=self.id)
                                     .order_by('problem__type_ege__number')
        ]

    def __str__(self):
        return f'вариант с id {self.id}'
