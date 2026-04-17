from django.http import Http404
from django.db.models import Count
from django.views.decorators.cache import cache_page
from django.views.generic.list import ListView
from problems.filters import ProblemTypeFilter
from problems.models import Problem, TypeInEGE


class TypesView(ListView):
    model = TypeInEGE
    template_name = 'typesinege/types.html'
    context_object_name = 'types'

    def get_queryset(self):
        return (
            TypeInEGE.objects
            .filter(number__lte=30)
            .values('number')
            .annotate(problems_count=Count('problems'))
            .order_by('number')
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        types = list(context['types'])
        context['first_part_types'] = [item for item in types if item['number'] <= 20]
        context['second_part_types'] = [item for item in types if item['number'] >= 21]
        return context


class ProblemsView(ListView):
    model = Problem
    template_name = 'problems/problems_list.html'
    context_object_name = 'problems'
    filter = ProblemTypeFilter
    paginate_by = 40

    def get_queryset(self):
        number = self.kwargs['number']
        self.types = TypeInEGE.objects.filter(number=number)
        if not self.types.exists():
            raise Http404
        queryset = Problem.objects.filter(type_ege__number=number).order_by('id')
        self.filterset = self.filter(self.request.GET, queryset=queryset)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        num = self.kwargs['number']
        data['filter'] = ProblemTypeFilter(self.request.GET,
                                           queryset=self.get_queryset())
        data['title'] = f'Тип {num}'
        data['next_type'] = (TypeInEGE.objects
                                      .all()
                                      .filter(number=int(num) + 1)
                                      .exists())
        data['previous_type'] = (TypeInEGE.objects
                                          .all()
                                          .filter(number=int(num) - 1)
                                          .exists())
        data['type_num'] = num
        return data

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = cache_page(30 * 60)(view)
        return view
