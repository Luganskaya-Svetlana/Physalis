from django.views.generic.detail import DetailView
from problems.models import Problem


class ProblemView(DetailView):
    model = Problem
    template_name = 'problems/problem_detail.html'
    context_object_name = 'problem'
