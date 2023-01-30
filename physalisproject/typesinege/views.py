from django.views.generic.list import ListView
from problems.models import TypeInEGE


class TypesView(ListView):
    model = TypeInEGE
    template_name = 'typesinege/types.html'
    context_object_name = 'types'

    def get_queryset(self):
        return super().get_queryset().order_by('number')
