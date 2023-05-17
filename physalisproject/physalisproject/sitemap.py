from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.contrib.flatpages.models import FlatPage
from problems.models import Problem

class StaticViewSitemap(Sitemap):
    # priority = 0.5
    # changefreq = 'monthly'

    def items(self):
        # return ['problems:list', 'typesinege:list', 'variants:list']
        return ['typesinege:list', 'variants:list']

    def location(self, item):
        return reverse(item)


class FlatPageSitemap(Sitemap):
    # changefreq = 'monthly'

    def items(self):
        return FlatPage.objects.exclude(url='/presentation')

class ProblemSitemap(Sitemap):
    def items(self):
        return Problem.objects.all()

    def location(self, item):
        return reverse('problems:detail', args=[item.pk])
