from django.contrib import admin

from .models import Category, PartOfEGE, Problem, Source, Tag, TypeInEGE


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    fields = ('text', 'solution', 'answer', 'complexity', 'source', 'category',
              'tags', 'part_ege', 'type_ege')
    list_display = ('id', 'author', 'date')
    filter_horizontal = ('tags',)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
        super().save_model(
            request=request,
            obj=obj,
            form=form,
            change=change
        )


admin.site.register(Category)
admin.site.register(PartOfEGE)
admin.site.register(Source)
admin.site.register(Tag)
admin.site.register(TypeInEGE)
