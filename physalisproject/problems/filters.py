import django_filters

from .models import Problem


class ProblemTypeFilter(django_filters.FilterSet):
    complexity = django_filters.NumberFilter()
    complexity__gt = django_filters.NumberFilter(field_name='complexity',
                                                 lookup_expr='gt',
                                                 label='Сложность больше, чем')
    complexity__lt = django_filters.NumberFilter(field_name='complexity',
                                                 lookup_expr='lt',
                                                 label='Сложность меньше, чем')

    class Meta:
        model = Problem
        fields = ['author', 'category', 'subcategory', 'source']
