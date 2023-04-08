import django_filters

from .models import Problem, PartOfEGE


class ProblemFilter(django_filters.FilterSet):
    complexity = django_filters.RangeFilter(field_name='complexity')
    text = django_filters.CharFilter(lookup_expr='icontains')
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
