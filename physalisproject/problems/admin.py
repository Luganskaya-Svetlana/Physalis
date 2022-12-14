from django.contrib import admin
from django.db.models import Count

from .models import (Category, PartOfEGE, Problem, Source, Subcategory, Tag,
                     TypeInEGE)


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    '''Настройки админки для задач'''
    fields = ('text', 'solution', 'answer', 'complexity', 'source', 'category',
              'subcategory', 'tags', 'type_ege')  # поля, отображаемые в форме
    list_display = ('id', 'type_ege', 'author', 'date')
    # поля, отображаемые на странице со всеми задачами

    filter_horizontal = ('tags',)

    def save_model(self, request, obj, form, change):
        if not change:  # если объект создается, а не меняется
            obj.author = request.user  # сохраняем автора
        super().save_model(
            request=request,
            obj=obj,
            form=form,
            change=change
        )


@admin.register(TypeInEGE)
class TypeInEGEAdmin(admin.ModelAdmin):
    '''Настройки админки типов задач в ЕГЭ'''
    fields = ('number', 'max_score', 'part_ege')
    list_display = ('number', 'problems_count')

    @admin.display(description='количество задач')
    def problems_count(self, obj):
        return obj.problems_count

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(problems_count=Count('problems'))
        # для каждого объекта сохраняем количество связанных с ним задач
        return queryset


# регистрируем все модели, чтобы они отображались в админке
admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(PartOfEGE)
admin.site.register(Source)
admin.site.register(Tag)
