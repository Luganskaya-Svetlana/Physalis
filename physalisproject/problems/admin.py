from django.contrib import admin
from itertools import combinations

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

    class Media:
        js = ('admin/js/problem_change_form.js',)

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
        if change and obj.pk:
            obj._previous_similar_problem_ids = set(
                Problem.objects
                .filter(pk=obj.pk)
                .values_list('similar_problems__id', flat=True)
            ) - {None}
        else:
            obj._previous_similar_problem_ids = set()

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

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)

        obj = form.instance
        previous_ids = getattr(obj, '_previous_similar_problem_ids', set())
        current_ids = set(obj.similar_problems.values_list('id', flat=True))
        selected_component_ids = self.get_connected_problem_ids(
            seed_ids=current_ids,
            exclude_ids={obj.id},
        )
        affected_ids = previous_ids | selected_component_ids | {obj.id}
        affected_problems = Problem.objects.in_bulk(affected_ids)

        preserved_components = self.get_components(
            problem_ids=affected_ids - {obj.id},
            exclude_ids={obj.id},
        )
        merged_component_ids = set()
        current_seed_ids = current_ids & (affected_ids - {obj.id})

        for component_ids in preserved_components:
            if component_ids & current_seed_ids:
                merged_component_ids |= component_ids

        for left_id, right_id in combinations(sorted(affected_ids), 2):
            affected_problems[left_id].similar_problems.remove(right_id)

        for component_ids in preserved_components:
            if component_ids & merged_component_ids:
                continue
            for left_id, right_id in combinations(sorted(component_ids), 2):
                affected_problems[left_id].similar_problems.add(right_id)

        if merged_component_ids:
            clique_ids = sorted(merged_component_ids | {obj.id})
            for left_id, right_id in combinations(clique_ids, 2):
                affected_problems[left_id].similar_problems.add(right_id)

    @staticmethod
    def get_connected_problem_ids(seed_ids, exclude_ids=None):
        exclude_ids = set(exclude_ids or [])
        pending_ids = set(seed_ids) - exclude_ids
        connected_ids = set()

        while pending_ids:
            batch_ids = pending_ids - connected_ids
            if not batch_ids:
                break

            connected_ids |= batch_ids
            neighbour_ids = set(
                Problem.objects
                .filter(pk__in=batch_ids)
                .values_list('similar_problems__id', flat=True)
            ) - {None}
            pending_ids |= neighbour_ids - exclude_ids

        return connected_ids

    def get_components(self, problem_ids, exclude_ids=None):
        remaining_ids = set(problem_ids) - set(exclude_ids or [])
        components = []

        while remaining_ids:
            root_id = next(iter(remaining_ids))
            component_ids = self.get_connected_problem_ids(
                seed_ids={root_id},
                exclude_ids=exclude_ids,
            )
            components.append(component_ids)
            remaining_ids -= component_ids

        return components


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
        'optional_laws',
        'justifications',
        'excluded_justifications',
    )
    list_display = ('id', 'problem', 'title', 'order', 'is_active')
    search_fields = ('problem__text', 'title')
    raw_id_fields = ('problem',)
    filter_horizontal = (
        'laws',
        'optional_laws',
        'justifications',
        'excluded_justifications',
    )
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
