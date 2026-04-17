from django.contrib import admin

from .forms import ImageForm
from .models import (
    Category,
    Image,
    Justification,
    JustificationGroup,
    Law,
    PartOfEGE,
    Problem,
    ProblemSolutionMethod,
    Source,
    Subcategory,
    Tag,
    TypeInEGE,
)

class ImageInline(admin.TabularInline):
    form = ImageForm
    model = Image
    fields = ('path_to_image',)

class JustificationGroupInline(admin.TabularInline):
    model = JustificationGroup
    fields = ('title', 'order', 'min_selected', 'max_selected')
    extra = 0
    show_change_link = True
    verbose_name = 'группа обоснований'
    verbose_name_plural = 'группы обоснований'

class ProblemSolutionMethodInline(admin.TabularInline):
    model = ProblemSolutionMethod
    fields = ('title', 'order', 'is_active')
    extra = 0
    show_change_link = True
    verbose_name = 'способ решения'
    verbose_name_plural = 'способы решения'


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    '''Настройки админки для задач'''
    view_on_site = staticmethod(lambda obj: obj.get_absolute_url())
    fields = (
        'text', 'solution', 'answer', 'complexity', 'source', 'category',
        'subcategory', 'tags', 'type_ege', 'similar_problems', 'notes',
        'get_solution_methods',
    )
    list_display = ('id', 'type_ege', 'author', 'date', 'get_variants')
    search_fields = ('id', 'text')
    filter_horizontal = ('tags',)
    inlines = (ImageInline, ProblemSolutionMethodInline)
    raw_id_fields = ('similar_problems',)
    readonly_fields = ('get_solution_methods',)

    @admin.display(description='варианты')
    def get_variants(self, obj):
        return ', '.join([str(var.id) for var in obj.variants.all()])

    @admin.display(description='способы решения')
    def get_solution_methods(self, obj):
        if not obj or not obj.pk:
            return '—'
        return ', '.join(
            method.title or f'Вариант {method.order}'
            for method in obj.solution_methods.all()
        ) or '—'

    def save_model(self, request, obj, form, change):
        if not change:
            obj.author = request.user
        if obj.subcategory:
            obj.category = obj.subcategory.category
        super().save_model(
            request=request,
            obj=obj,
            form=form,
            change=change
        )
        s_problems = list(obj.similar_problems.all())
        for i in range(len(s_problems)):
            for j in range(i + 1, len(s_problems)):
                s_problems[i].similar_problems.add(s_problems[j])


@admin.register(TypeInEGE)
class TypeInEGEAdmin(admin.ModelAdmin):
    '''Настройки админки типов задач в ЕГЭ'''
    view_on_site = staticmethod(lambda obj: obj.get_absolute_url())
    fields = ('number', 'max_score', 'part_ege')
    list_display = ('number', 'problems_count')

    @admin.display(description='количество задач')
    def problems_count(self, obj):
        return obj.problems_count


@admin.register(Law)
class LawAdmin(admin.ModelAdmin):
    fields = ('name', 'order')
    list_display = ('id', 'name', 'order')
    search_fields = ('name',)
    ordering = ('order', 'name')


@admin.register(Justification)
class JustificationAdmin(admin.ModelAdmin):
    fields = ('text', 'order')
    list_display = ('id', 'short_text', 'order')
    search_fields = ('text',)
    ordering = ('order', 'text')

    @admin.display(description='текст')
    def short_text(self, obj):
        return obj.text[:120]


@admin.register(JustificationGroup)
class JustificationGroupAdmin(admin.ModelAdmin):
    fields = ('method', 'title', 'order', 'min_selected', 'max_selected', 'justifications')
    list_display = ('id', 'method', 'title', 'order', 'min_selected', 'max_selected')
    search_fields = ('title', 'method__title', 'method__problem__id')
    raw_id_fields = ('method',)
    filter_horizontal = ('justifications',)


@admin.register(ProblemSolutionMethod)
class ProblemSolutionMethodAdmin(admin.ModelAdmin):
    fields = (
        'problem',
        'title',
        'order',
        'is_active',
        'laws',
        'justifications',
        'excluded_justifications',
    )
    list_display = ('id', 'problem', 'title', 'order', 'is_active')
    search_fields = ('problem__text', 'title')
    raw_id_fields = ('problem',)
    filter_horizontal = ('laws', 'justifications', 'excluded_justifications')
    list_filter = ('is_active',)
    inlines = (JustificationGroupInline,)


@admin.register(PartOfEGE)
class PartOfEGEAdmin(admin.ModelAdmin):
    fields = ('name',)
    list_display = ('id', 'name')
    search_fields = ('name',)

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

admin.site.register(Category)
admin.site.register(Subcategory)
admin.site.register(Source)
admin.site.register(Tag)
