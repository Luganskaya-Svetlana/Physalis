from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import Variant


class VariantForm(forms.ModelForm):
    class Meta:
        model = Variant
        fields = ('problems', 'text', 'complexity', 'is_full', 'show_answers')

    def clean(self):
        '''Проверка на то, является ли вариант полным,
        и вычисление его сложности
        '''

        NUMBER_OF_PROBLEMS = 30  # количество задач в полном варианте

        cleaned_data = super().clean()
        comlexity = 0
        problems = cleaned_data.get('problems')
        problems_count = len(problems)

        if cleaned_data.get('is_full'):  # если выбрана опция "полный вариант"
            if problems_count == NUMBER_OF_PROBLEMS:
                num = 1
                problems = problems.order_by('type_ege__number')
                for problem in problems:
                    if problem.type_ege.number != num:
                        raise ValidationError('Это не полный вариант.'
                                              ' Первая неверная задача:'
                                              f' {problem.id} (тип '
                                              f'{problem.type_ege.number})')
                    num += 1
                    comlexity += problem.complexity
            else:
                raise ValidationError('Это не полный вариант. '
                                      'Число задач меньше, чем'
                                      f' {NUMBER_OF_PROBLEMS}')
        else:  # если опция "полный вариант" не выбрана
            for problem in problems:
                comlexity += problem.complexity
        cleaned_data['complexity'] = round(comlexity / problems_count, 1)
        return cleaned_data


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    '''Настройки админки для вариантов'''
    form = VariantForm
    readonly_fields = ('date',)
    fieldsets = (
        (None, {'fields': ('problems', 'text', 'is_full', 'show_answers',)}),
        (('Автозаполняемые поля'), {
            'classes': ('collapse',),
            'fields': (
                'date',
                'complexity'
            ),
        }),
    )
    # fields = ('problems', 'text', 'is_full', 'show_answers', 'date',
    #           'complexity')
    # поля, отображаемые в форме
    list_display = ('id', 'text', 'is_full')
    # поля, отображаемые на странице со всеми вариантами
    search_fields = ('id', 'text')  # поля, по которым осущ. поиск в админке
    raw_id_fields = ('problems',)
