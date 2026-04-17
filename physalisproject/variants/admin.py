from django import forms
from django.contrib import admin

from .models import Variant
from .services import calculate_variant_complexity, generate_answer_slug


class VariantForm(forms.ModelForm):
    class Meta:
        model = Variant
        fields = ('owner', 'problems', 'text', 'complexity', 'is_full', 'show_answers',
                  'notes', 'sort_by_complexity', 'sort_by_type', 'show_complexity', 'show_source',
                  'show_type', 'show_max_score', 'show_original_number',
                  'show_solution_link', 'is_published')

    def clean(self):
        cleaned_data = super().clean()
        problems = cleaned_data.get('problems')
        if problems:
            cleaned_data['complexity'] = calculate_variant_complexity(problems)
            if not self.instance.answer_slug:
                self.instance.answer_slug = generate_answer_slug()

        return cleaned_data


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    '''Настройки админки для вариантов'''
    view_on_site = staticmethod(lambda obj: obj.get_absolute_url())
    form = VariantForm
    readonly_fields = ('date',)
    fieldsets = (
        (None, {'fields': ('owner', 'problems', 'text', 'is_full',
                           'sort_by_complexity',
                           'sort_by_type',
                           'show_complexity',
                           'show_source',
                           'show_type',
                           'show_max_score',
                           'show_original_number',
                           'show_solution_link',
                           'show_answers',
                           'is_published', 'notes')}),
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
    list_display = ('id', 'owner', 'text', 'is_full', 'is_published')
    # поля, отображаемые на странице со всеми вариантами
    search_fields = ('id', 'text')  # поля, по которым осущ. поиск в админке
    raw_id_fields = ('owner', 'problems',)

    def save_model(self, request, obj, form, change):
        if not change and not obj.owner:
            obj.owner = request.user
        super().save_model(request, obj, form, change)
