from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from problems.models import Image, Problem
from problems.filters import ProblemFilter


class ProblemView(DetailView):
    model = Problem
    template_name = 'problems/problem_detail.html'
    context_object_name = 'problem'

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        problem_pk = self.kwargs['pk']
        images = Image.objects.filter(problem_id=problem_pk)
        data['text_images'] = images.filter(relation=1)
        data['solution_images'] = images.filter(relation=2)
        data['answer_images'] = images.filter(relation=3)
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

    def get_queryset(self):
        return Problem.objects.filter().order_by('id')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['filter'] = ProblemFilter(self.request.GET,
                                       queryset=self.get_queryset())
        data['title'] = 'Все задачи'
        return data
