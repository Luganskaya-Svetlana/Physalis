from django.contrib import admin

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


# регистрируем все модели, чтобы они отображались в админке
admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(PartOfEGE)
admin.site.register(Source)
admin.site.register(Tag)
admin.site.register(TypeInEGE)
