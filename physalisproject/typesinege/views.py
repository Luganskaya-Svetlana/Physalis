from django.shortcuts import get_object_or_404
from django.views.generic.list import ListView
from problems.models import Problem, TypeInEGE


class TypesView(ListView):
    model = TypeInEGE
    template_name = 'typesinege/types.html'
    context_object_name = 'types'

    def get_queryset(self):
        return super().get_queryset().order_by('number')


class ProblemsView(ListView):
    model = Problem
    template_name = 'typesinege/problems.html'
    context_object_name = 'problems'

    def get_queryset(self):
        number = self.kwargs['number']
        self.type = get_object_or_404(TypeInEGE, number=number)
        return Problem.objects.filter(type_ege=self.type)
