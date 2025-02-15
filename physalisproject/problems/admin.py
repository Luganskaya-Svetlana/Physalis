from django.contrib import admin

from .forms import ImageForm
from .models import (Category, Image, PartOfEGE, Problem, Source, Subcategory,
                     Tag, TypeInEGE)


class ImageInline(admin.TabularInline):
    form = ImageForm
    model = Image
    fields = ('path_to_image',)


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    '''Настройки админки для задач'''
    fields = ('text', 'solution', 'answer', 'complexity', 'source', 'category',
              'subcategory', 'tags', 'type_ege', 'similar_problems', 'notes',)
    # поля, отображаемые в форме
    list_display = ('id', 'type_ege', 'author', 'date', 'get_variants')
    # поля, отображаемые на странице со всеми задачами
    search_fields = ('id', 'text')  # поля, по которым осущ. поиск в админке
    filter_horizontal = ('tags',)
    inlines = (ImageInline,)
    raw_id_fields = ('similar_problems',)

    @admin.display(description='варианты')
    def get_variants(self, obj):
        return ', '.join([str(var.id) for var in obj.variants.all()])

    def save_model(self, request, obj, form, change):
        if not change:  # если объект создается, а не меняется
            obj.author = request.user  # сохраняем автора
        if obj.subcategory:
            obj.category = obj.subcategory.category
        super().save_model(
            request=request,
            obj=obj,
            form=form,
            change=change
        )
        s_problems = obj.similar_problems.get_queryset()
        for i in range(len(s_problems)):
            for j in range(i + 1, len(s_problems)):
                s_problems[i].similar_problems.add(s_problems[j])


@admin.register(TypeInEGE)
class TypeInEGEAdmin(admin.ModelAdmin):
    '''Настройки админки типов задач в ЕГЭ'''
    fields = ('number', 'max_score', 'part_ege')
    list_display = ('number', 'problems_count')

    @admin.display(description='количество задач')
    def problems_count(self, obj):
        return obj.problems_count


# регистрируем все модели, чтобы они отображались в админке
admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(PartOfEGE)
admin.site.register(Source)
admin.site.register(Tag)
