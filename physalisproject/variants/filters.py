from django_filters import FilterSet
from variants.models import Variant


class VariantFilter(FilterSet):
    class Meta:
        model = Variant
        fields = ['is_full']
