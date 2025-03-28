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

    problems = SortedManyToManyField(Problem,
                                     verbose_name='задачи')
    text = models.TextField('описание', blank=True, null=True)
    complexity = models.FloatField('сложность', blank=True, default=0)
    is_full = models.BooleanField('полный вариант', default=True)
    show_answers = models.BooleanField('показать решения', default=True)
    date = models.DateField('дата добавления', auto_now_add=True)
    answer_slug = models.SlugField('slug для получения ответов',
                                   max_length=4, unique=False,
                                   blank=True, default='',
                                   validators=[validate_answer_slug])
    is_published = models.BooleanField('показывать в списке вариантов',
                                       default=True)
    notes = models.TextField('заметки', blank=True, null=True)

    class Meta:
        verbose_name = 'вариант'
        verbose_name_plural = 'варианты'
        default_related_name = 'variants'

    def get_problems(self):  # задачи для страницы варианта
        problems = (self.problems
                        .only('text', 'type_ege__number'))
        if self.is_full and (None,) not in problems.values_list('type_ege'):
            problems = problems.order_by('type_ege__number')
        return problems

    def get_answers(self):  # задачи для страницы с ответами
        problems = (self.problems
                        .only('solution', 'answer', 'type_ege__max_score',
                              'complexity', 'source', 'id'))
        if self.is_full and (None,) not in problems.values_list('type_ege'):
            problems = problems.order_by('type_ege__number')
        return problems

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
