from django.views.generic.list import ListView
from variants.models import Variant


class VariantsView(ListView):
    model = Variant
    template_name = 'variants/variants_list.html'
    context_object_name = 'variants'

    def get_queryset(self):
        return Variant.objects.list()
