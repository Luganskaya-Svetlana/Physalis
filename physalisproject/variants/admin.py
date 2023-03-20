from django.contrib import admin

from .models import Variant


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    '''Настройки админки для вариантов'''
    fields = ('problems', 'text', 'complexity', 'is_full', 'show_answers')
    # поля, отображаемые в форме
    list_display = ('id', 'text', 'is_full')
    # поля, отображаемые на странице со всеми вариантами
    search_fields = ('id', 'text')  # поля, по которым осущ. поиск в админке
    raw_id_fields = ('problems',)

    # def save_model(self, request, obj, form, change):
    #     obj.save()
    #     NUMBER_OF_PROBLEMS = 30  # количество задач в полном варианте
    #     problems = obj.get_problems()
    #     print(problems, len(problems))
    #     if NUMBER_OF_PROBLEMS != len(problems):
    #         obj.is_full = False
    #     else:
    #         obj.is_full = True
    #     super().save_model(
    #         request=request,
    #         obj=obj,
    #         form=form,
    #         change=change
    #     )
