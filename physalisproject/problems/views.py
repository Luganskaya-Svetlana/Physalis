from django.views.generic.detail import DetailView
from problems.models import Image, Problem


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
        return data
