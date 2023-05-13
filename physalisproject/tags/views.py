from django.shortcuts import get_object_or_404
from django.views.decorators.cache import cache_page
from django.views.generic.list import ListView
from problems.filters import ProblemTagFilter
from problems.models import Problem, Tag


class TagsView(ListView):
    model = Tag
    template_name = 'tags/tags_list.html'
    context_object_name = 'tags'

    def get_queryset(self):
        return super().get_queryset()


class ProblemsView(ListView):
    model = Problem
    template_name = 'problems/problems_list.html'
    context_object_name = 'problems'
    filter = ProblemTagFilter
    paginate_by = 40

    def get_queryset(self):
        slug = self.kwargs['slug']
        self.tag = get_object_or_404(Tag, slug=slug)
        queryset = Problem.objects.filter(tags__id=self.tag.id).order_by('id')
        self.filterset = self.filter(self.request.GET, queryset=queryset)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['filter'] = ProblemTagFilter(self.request.GET,
                                          queryset=self.get_queryset())
        data['title'] = self.tag.name
        return data

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = cache_page(60 * 60)(view)
        return view
