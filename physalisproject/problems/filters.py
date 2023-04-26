import django_filters

from .models import PartOfEGE, Problem


class ProblemFilter(django_filters.FilterSet):
    complexity = django_filters.RangeFilter(field_name='complexity')
    text = django_filters.CharFilter(lookup_expr='icontains',
                                     label='Поиск по тексту')
    part_ege = django_filters.filters.ModelChoiceFilter(
        field_name='type_ege__part_ege',
        queryset=PartOfEGE.objects.all(),
        label='Часть ЕГЭ'
    )

    class Meta:
        model = Problem
        fields = ['id', 'text', 'category', 'subcategory', 'source',
                  'part_ege']


class ProblemTypeFilter(django_filters.FilterSet):
    complexity = django_filters.RangeFilter(field_name='complexity')

    class Meta:
        model = Problem
        fields = ['category', 'subcategory', 'source']


class ProblemTagFilter(django_filters.FilterSet):
    complexity = django_filters.RangeFilter(field_name='complexity')
    type_ege = django_filters.NumberFilter(field_name='type_ege__number',
                                           label='Номер в ЕГЭ')

    class Meta:
        model = Problem
        fields = ['category', 'subcategory', 'source', 'type_ege']
