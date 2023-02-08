import django_filters

from .models import Problem


class ProblemTypeFilter(django_filters.FilterSet):
    complexity = django_filters.RangeFilter(field_name='complexity')

    class Meta:
        model = Problem
        fields = ['author', 'category', 'subcategory', 'source']
