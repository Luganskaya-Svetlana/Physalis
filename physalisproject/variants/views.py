from django.http import Http404
from django.views.decorators.cache import cache_page
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from variants.filters import VariantFilter
from variants.models import Variant


class VariantsView(ListView):
    model = Variant
    template_name = 'variants/variants_list.html'
    context_object_name = 'variants'
    paginate_by = 30
    filter = VariantFilter

    def get_queryset(self):
        queryset = Variant.objects.list()
        pars = self.request.GET
        if 'order_by' in pars.keys() and pars['order_by'] in ('complexity',
                                                              'id',
                                                              '-complexity',
                                                              '-id'):
            order_by = self.request.GET['order_by']
        else:
            order_by = 'id'
        self.filterset = self.filter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by(order_by)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['filter'] = VariantFilter(self.request.GET)
        data['title'] = 'Варианты'
        return data

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = cache_page(60 * 60)(view)
        return view


class VariantView(DetailView):
    model = Variant
    template_name = 'variants/variant_detail.html'
    context_object_name = 'variant'

    def get_queryset(self):
        return Variant.objects.detail()

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = cache_page(60 * 60)(view)
        return view


class VariantAnswerView(DetailView):
    model = Variant
    template_name = 'variants/variant_answer.html'
    context_object_name = 'variant'

    def get_queryset(self):
        return Variant.objects.answers()

    def get_object(self, queryset=None):
        variant = super().get_object(queryset)
        slug = self.kwargs.get(self.slug_url_kwarg)
        if variant.answer_slug == slug:
            return variant
        else:
            raise Http404

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = cache_page(60 * 60)(view)
        return view
