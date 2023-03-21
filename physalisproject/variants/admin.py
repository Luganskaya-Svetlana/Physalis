from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import Variant


class VariantForm(forms.ModelForm):
    class Meta:
        model = Variant
        fields = ('problems', 'text', 'complexity', 'is_full', 'show_answers')

    def clean(self):
        NUMBER_OF_PROBLEMS = 30  # количество задач в полном варианте

        cleaned_data = super().clean()
        if cleaned_data.get('is_full'):  # если выбрана опция "полный вариант"
            problems = cleaned_data.get('problems')
            if len(problems) == NUMBER_OF_PROBLEMS:
                num = 1
                problems = problems.order_by('type_ege__number')
                for problem in problems:
                    if problem.type_ege.number != num:
                        raise ValidationError('Это не полный вариант.'
                                              ' Первая неверная задача:'
                                              f' {problem.id} (тип '
                                              f'{problem.type_ege.number})')
                    num += 1
            else:
                raise ValidationError('Это не полный вариант. '
                                      'Число задач меньше, чем'
                                      f' {NUMBER_OF_PROBLEMS}')
        return cleaned_data


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    '''Настройки админки для вариантов'''
    form = VariantForm
    fields = ('problems', 'text', 'complexity', 'is_full', 'show_answers')
    # поля, отображаемые в форме
    list_display = ('id', 'text', 'is_full')
    # поля, отображаемые на странице со всеми вариантами
    search_fields = ('id', 'text')  # поля, по которым осущ. поиск в админке
    raw_id_fields = ('problems',)
