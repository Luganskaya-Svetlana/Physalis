from django import forms

from .services import (
    get_default_generation_options,
    get_selection_problem_ids,
    get_selection_problems,
    normalize_generation_options,
    validate_full_variant,
)


class VariantGenerationForm(forms.Form):
    is_full = forms.BooleanField(
        label='Полный вариант',
        required=False,
    )
    show_answers = forms.BooleanField(
        label='Показать решения',
        required=False,
    )
    sort_by_complexity = forms.BooleanField(
        label='Отсортировать по возрастанию сложности',
        required=False,
        initial=False,
    )
    show_complexity = forms.BooleanField(
        label='сложность',
        required=False,
        initial=False,
    )
    show_source = forms.BooleanField(
        label='источник',
        required=False,
        initial=False,
    )
    show_type = forms.BooleanField(
        label='тип (номер в ЕГЭ)',
        required=False,
        initial=False,
    )
    show_max_score = forms.BooleanField(
        label='максимум баллов',
        required=False,
        initial=False,
    )
    show_original_number = forms.BooleanField(
        label='оригинальный номер',
        required=False,
        initial=False,
    )
    show_solution_link = forms.BooleanField(
        label='ссылку на решение',
        required=False,
        initial=False,
    )
    is_published = forms.BooleanField(
        label='Показывать в списке вариантов',
        required=False,
    )

    def __init__(self, *args, request=None, is_admin=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = request
        self.is_admin = is_admin
        self.label_suffix = ''

        if not is_admin:
            self.fields.pop('is_published')

        if not self.is_bound:
            for field_name, value in get_default_generation_options(is_admin=is_admin).items():
                if field_name in self.fields:
                    self.fields[field_name].initial = value

    def clean(self):
        cleaned_data = super().clean()

        if self.request is None:
            return cleaned_data

        selected_ids = get_selection_problem_ids(self.request)
        if not selected_ids:
            raise forms.ValidationError('Сначала выберите хотя бы одну задачу.')

        problems = get_selection_problems(self.request)
        if cleaned_data.get('is_full'):
            validate_full_variant(problems, is_full=True)
            cleaned_data['sort_by_complexity'] = False

        normalized = normalize_generation_options(cleaned_data)
        for field_name, value in normalized.items():
            if field_name in cleaned_data:
                cleaned_data[field_name] = value

        return cleaned_data
