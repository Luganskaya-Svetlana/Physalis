from django.views.generic.list import ListView
from variants.filters import VariantFilter
from variants.models import Variant


class VariantsView(ListView):
    model = Variant
    template_name = 'variants/variants_list.html'
    context_object_name = 'variants'
    filter = VariantFilter

    def get_queryset(self):
        queryset = Variant.objects.list()
        params = self.request.GET
        if 'order_by' in params.keys() and params['order_by'] in ('complexity',
                                                                  'date'):
            order_by = self.request.GET['order_by']
        else:
            order_by = 'id'
        self.filterset = self.filter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by(order_by)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['filter'] = VariantFilter(self.request.GET,
                                       queryset=self.get_queryset())
        data['title'] = 'Варианты'
        return data
