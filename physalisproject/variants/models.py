from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse
from problems.models import Problem
from sortedm2m.fields import SortedManyToManyField
from variants.managers import VariantManager

from .validators import validate_answer_slug

# from django.core.files.base import ContentFile
# from io import BytesIO
# from django.template.loader import get_template
# from xhtml2pdf import pisa


class Variant(models.Model):
    objects = VariantManager()

    owner = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_variants',
        verbose_name='создатель',
    )
    problems = SortedManyToManyField(Problem,
                                     verbose_name='задачи')
    text = models.TextField('описание', blank=True, null=True)
    complexity = models.FloatField('сложность', blank=True, default=0)
    is_full = models.BooleanField('полный вариант', default=False)
    show_answers = models.BooleanField('показать решения', default=False)
    date = models.DateField('дата добавления', auto_now_add=True)
    answer_slug = models.SlugField('slug для получения ответов',
                                   max_length=4, unique=False,
                                   blank=True, default='',
                                   validators=[validate_answer_slug])
    is_published = models.BooleanField('показать в списке вариантов',
                                       default=False)
    notes = models.TextField('заметки', blank=True, null=True)
    sort_by_complexity = models.BooleanField('отсортировать по'
                                             ' нарастанию сложности',
                                             default=True)
    sort_by_type = models.BooleanField(
        'отсортировать по типу',
        default=False,
    )
    show_complexity = models.BooleanField(
        'отображать в варианте сложность',
        default=False,
    )
    show_source = models.BooleanField(
        'отображать в варианте источник',
        default=False,
    )
    show_type = models.BooleanField(
        'отображать в варианте тип',
        default=False,
    )
    show_max_score = models.BooleanField(
        'отображать в варианте максимум баллов',
        default=False,
    )
    show_original_number = models.BooleanField(
        'отображать в варианте оригинальный номер',
        default=False,
    )
    show_solution_link = models.BooleanField(
        'отображать в варианте ссылку на решение',
        default=False,
    )

    class Meta:
        verbose_name = 'вариант'
        verbose_name_plural = 'варианты'
        default_related_name = 'variants'

    def _get_sorted_problems(self, problems):
        problems = list(problems)
        indexed = list(enumerate(problems))

        if self.sort_by_type:
            indexed.sort(
                key=lambda pair: (
                    pair[1].type_ege.number if pair[1].type_ege_id is not None else 10**6,
                    pair[1].complexity or 0,
                    pair[0],
                )
            )
            return [problem for _, problem in indexed]

        if self.sort_by_complexity:
            indexed.sort(key=lambda pair: ((pair[1].complexity or 0), pair[0]))
            return [problem for _, problem in indexed]

        if self.is_full and all(problem.type_ege_id is not None for problem in problems):
            indexed.sort(key=lambda pair: (pair[1].type_ege.number, pair[0]))
            return [problem for _, problem in indexed]

        return problems

    def get_problems(self):  # задачи для страницы варианта
        problems = (self.problems
                    .select_related('type_ege', 'source')
                    .only(
                        'id',
                        'text',
                        'type_ege__number',
                        'type_ege__max_score',
                        'complexity',
                        'source__name',
                    ))
        return self._get_sorted_problems(problems)

    def get_answers(self):  # задачи для страницы с ответами
        problems = (self.problems
                    .select_related('type_ege', 'source')
                    .only('solution', 'answer', 'type_ege__max_score',
                          'type_ege__number', 'complexity', 'source__name', 'id'))
        return self._get_sorted_problems(problems)

    def __str__(self):
        return f'вариант с id {self.id}'

    def get_absolute_url(self):
        return reverse('variants:detail', kwargs={'pk': self.pk})

    def get_answers_url(self):
        return reverse('variants:answers', kwargs={'pk': self.pk,
                                                   'slug': self.answer_slug})

    # def generate_pdf(self):
    #     template = get_template('variants/variant_detail.html')
    #     context = {'variant': self}
    #     html_content = template.render(context)
    #     pdf_buffer = BytesIO()
    #     pisa.CreatePDF(html_content, dest=pdf_buffer)
    #     pdf_content = pdf_buffer.getvalue()
    #     pdf_buffer.close()
    #     return pdf_content

    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)
    #     pdf_content = self.generate_pdf()
    #     pdf_filename = f'variant_{self.pk}.pdf'
    #     self.pdf_file.save(pdf_filename, ContentFile(pdf_content))
    #     super().save(update_fields=['pdf_file'])

    # pdf_file = models.FileField('PDF файл варианта',
    #                             upload_to='variants_pdf/',
    #                             null=True, blank=True)
