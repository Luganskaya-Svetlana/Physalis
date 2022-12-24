from django.contrib import admin

from .models import Category, PartOfEGE, Problem, Source, Tag, TypeInEGE


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    fields = ('text', 'solution', 'answer', 'complexity', 'source', 'category',
              'tags', 'part_ege', 'type_ege')
    filter_horizontal = ('tags',)


admin.site.register(Category)
admin.site.register(PartOfEGE)
admin.site.register(Source)
admin.site.register(Tag)
admin.site.register(TypeInEGE)
