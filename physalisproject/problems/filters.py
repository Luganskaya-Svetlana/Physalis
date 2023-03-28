import django_filters

from .models import Problem


class ProblemFilter(django_filters.FilterSet):
    complexity = django_filters.RangeFilter(field_name='complexity')
    text = django_filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = Problem
        fields = ['id', 'text', 'author', 'category', 'subcategory', 'source',
                  'type_ege__part_ege']


class ProblemTypeFilter(django_filters.FilterSet):
    complexity = django_filters.RangeFilter(field_name='complexity')

    class Meta:
        model = Problem
        fields = ['author', 'category', 'subcategory', 'source']
