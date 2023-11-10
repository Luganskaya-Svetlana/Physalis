from random import choice
from string import ascii_lowercase as letters

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import Variant


class VariantForm(forms.ModelForm):
    class Meta:
        model = Variant
        fields = ('problems', 'text', 'complexity', 'is_full', 'show_answers')

    def clean(self):
        cleaned_data = super().clean()
        comlexity = 0
        problems = cleaned_data.get('problems')
        '''Проверка на то, является ли вариант полным
        (теперь вручную)
        '''
        # NUMBER_OF_PROBLEMS = 26  # количество задач в полном варианте
        # if problems:  # если указаны существующие задачи
        #     if cleaned_data.get('is_full'):
        #         # проверяем, действительно ли вариант полный
        #         types = sorted([problem.type_ege.number
        #                         for problem in problems])
        #         i = 1
        #         to_add = []
        #         to_remove = []
        #         while i != NUMBER_OF_PROBLEMS + 1:
        #             if types:
        #                 current_type = types.pop(0)
        #                 if i > current_type:
        #                     if str(current_type) not in to_remove:
        #                         to_remove.append(str(current_type))
        #                 elif i < current_type:
        #                     while i != current_type:
        #                         to_add.append(str(i))
        #                         i += 1
        #                     i += 1
        #                 elif i == current_type:
        #                     i += 1
        #             else:
        #                 to_add.append(str(i))
        #                 i += 1
        #         if types:
        #             for current_type in types:
        #                 if str(current_type) not in to_remove:
        #                     to_remove.append(str(current_type))
        #         if to_add and to_remove:
        #             raise ValidationError('Это не полный вариант. '
        #                                   'Слишком много задач с типами '
        #                                   f'{", ".join(to_remove)}. '
        #                                   'Нет задач с типами '
        #                                   f'{", ".join(to_add)}.')
        #         elif to_add:
        #             raise ValidationError('Это не полный вариант. '
        #                                   'Нет задач с типами '
        #                                   f'{", ".join(to_add)}.')
        #         elif to_remove:
        #             raise ValidationError('Это не полный вариант. '
        #                                   'Слишком много задач с типами '
        #                                   f'{", ".join(to_remove)}.')
        if problems:
            # расчет сложности варианта
            problems_count = len(problems)
            for problem in problems:
                comlexity += problem.complexity
            cleaned_data['complexity'] = round(comlexity / problems_count, 1)

            if not cleaned_data.get('answer_slug'):
                # если slug не указан, генерируем самостоятельно
                answer_slug = ''
                for _ in range(4):
                    answer_slug += choice(letters)
                cleaned_data['answer_slug'] = answer_slug

        return cleaned_data


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    '''Настройки админки для вариантов'''
    form = VariantForm
    readonly_fields = ('date',)
    fieldsets = (
        (None, {'fields': ('problems', 'text', 'is_full', 'show_answers',
                           'is_published')}),
        (('Автозаполняемые поля'), {
            'classes': ('collapse',),
            'fields': (
                'date',
                'complexity',
                'answer_slug'
            ),
        }),
    )
    # поля, отображаемые в форме
    list_display = ('id', 'text', 'is_full', 'is_published',)
    # поля, отображаемые на странице со всеми вариантами
    search_fields = ('id', 'text')  # поля, по которым осущ. поиск в админке
    raw_id_fields = ('problems',)
