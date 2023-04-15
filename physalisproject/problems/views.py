from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from problems.filters import ProblemFilter
from problems.models import Problem
from django.views.decorators.cache import cache_page


class ProblemView(DetailView):
    model = Problem
    template_name = 'problems/problem_detail.html'
    context_object_name = 'problem'

    def get_queryset(self):
        return Problem.objects.detail()

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        problem_pk = self.kwargs['pk']
        # для временной навигации:
        data['next_problem'] = (Problem.objects
                                       .all()
                                       .filter(id=int(problem_pk) + 1)
                                       .exists())
        data['previous_problem'] = (Problem.objects
                                           .all()
                                           .filter(id=int(problem_pk) - 1)
                                           .exists())
        return data


class ProblemsView(ListView):
    model = Problem
    template_name = 'problems/problems_list.html'
    context_object_name = 'problems'
    filter = ProblemFilter
    paginate_by = 40

    def get_queryset(self):
        queryset = Problem.objects.list()
        self.filterset = self.filter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by('id')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['filter'] = ProblemFilter(self.request.GET)
        data['title'] = 'Все задачи'
        return data


problems_view = cache_page(5 * 60)(ProblemsView.as_view())
