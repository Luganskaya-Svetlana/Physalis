from django.core.exceptions import ValidationError
from django.contrib.auth.views import redirect_to_login
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from problems.models import Problem

from variants.forms import VariantGenerationForm
from variants.filters import VariantFilter
from variants.models import Variant
from variants.services import (
    add_problem_to_selection,
    build_selection_summary,
    build_options_signature,
    clear_selection,
    clear_deleted_selection,
    create_variant,
    get_deleted_selection_problems,
    get_last_generated_variant_data,
    get_matching_last_generated_variant,
    get_default_generation_options,
    get_selection_problems,
    move_problem_in_selection,
    remove_problem_from_selection,
    restore_problem_to_selection,
    restore_all_deleted_problems,
    set_last_generated_variant_data,
    swap_problems_in_selection,
)
from accounts.permissions import can_manage_homework
from homework.models import HomeworkAssignment


class VariantsView(ListView):
    model = Variant
    template_name = 'variants/variants_list.html'
    context_object_name = 'variants'
    paginate_by = 30
    filter = VariantFilter

    def get_queryset(self):
        queryset = Variant.objects.list()
        pars = self.request.GET
        if 'order_by' in pars.keys() and pars['order_by'] in ('complexity',
                                                              'id',
                                                              '-complexity',
                                                              '-id'):
            order_by = self.request.GET['order_by']
        else:
            order_by = 'id'
        self.filterset = self.filter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by(order_by)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['filter'] = VariantFilter(self.request.GET)
        data['title'] = 'Варианты'
        return data

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = cache_page(60 * 60)(view)
        return view


class VariantView(DetailView):
    model = Variant
    template_name = 'variants/variant_detail.html'
    context_object_name = 'variant'

    def get_queryset(self):
        return Variant.objects.detail()

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        variant = data['variant']
        can_view_answers_link = bool(
            self.request.user.is_staff
            or (
                self.request.user.is_authenticated
                and variant.owner_id == self.request.user.id
            )
        )
        data['can_view_created_answers_link'] = can_view_answers_link
        data['can_assign_homework'] = can_manage_homework(self.request.user)
        if data['can_assign_homework']:
            user = self.request.user
            assignments = HomeworkAssignment.objects.filter(variant=variant)
            if not user.is_staff:
                assignments = assignments.filter(created_by=user)
            data['visible_homework_assignments'] = assignments.order_by('-created_at')[:5]
        else:
            data['visible_homework_assignments'] = []
        return data


class VariantAnswerView(DetailView):
    model = Variant
    template_name = 'variants/variant_answer.html'
    context_object_name = 'variant'

    def get_queryset(self):
        return Variant.objects.answers()

    def get_object(self, queryset=None):
        variant = super().get_object(queryset)
        slug = self.kwargs.get(self.slug_url_kwarg)
        if variant.answer_slug == slug:
            return variant
        else:
            raise Http404

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = cache_page(60 * 60)(view)
        return view


class CurrentVariantSelectionView(View):
    template_name = 'variants/variant_current.html'

    def ensure_access(self, request):
        if request.user.is_authenticated:
            return None
        return redirect_to_login(request.get_full_path(), '/admin/login/')

    def get_initial_form_options(self, request):
        last_generated = get_last_generated_variant_data(request)
        options = last_generated.get('options') or get_default_generation_options(
            is_admin=bool(getattr(request.user, 'is_staff', False))
        )
        if not getattr(request.user, 'is_staff', False):
            options.pop('is_published', None)
        return options

    def get_current_form_options(self, request, form=None):
        if form is None or not form.is_bound:
            return self.get_initial_form_options(request)

        fields = (
            'is_full',
            'show_answers',
            'sort_by_complexity',
            'sort_by_type',
            'show_complexity',
            'show_source',
            'show_type',
            'show_max_score',
            'show_original_number',
            'show_solution_link',
            'is_published',
        )
        options = {}
        for field_name in fields:
            if field_name not in form.fields:
                continue
            options[field_name] = bool(form.data.get(field_name))
        if options.get('is_full'):
            options['sort_by_complexity'] = False
        return options

    def get_context_data(self, request, form=None):
        problems = get_selection_problems(request)
        deleted_problems = get_deleted_selection_problems(request)
        summary = build_selection_summary(request)
        if form is None:
            form = VariantGenerationForm(
                request=request,
                is_admin=bool(getattr(request.user, 'is_staff', False)),
                initial=self.get_initial_form_options(request),
            )
        current_options = self.get_current_form_options(request, form=form)
        last_generated_variant = get_matching_last_generated_variant(
            request,
            options=current_options,
        )

        return {
            'title': 'Текущая подборка',
            'problems': problems,
            'deleted_problems': deleted_problems,
            'summary': summary,
            'form': form,
            'last_generated_variant': last_generated_variant,
            'last_generated_options_signature': build_options_signature(current_options),
        }

    def render_selection_html(self, request, form=None):
        context = self.get_context_data(
            request,
            form=form,
        )
        return render_to_string(
            'variants/_variant_current_content.html',
            context,
            request=request,
        )

    def get(self, request):
        denied = self.ensure_access(request)
        if denied is not None:
            return denied
        return render(request, self.template_name, self.get_context_data(request))

    def post(self, request):
        denied = self.ensure_access(request)
        if denied is not None:
            return denied
        action = request.POST.get('action')
        problem_id = request.POST.get('problem_id')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if action == 'remove' and problem_id:
            remove_problem_from_selection(request, int(problem_id))
            if is_ajax:
                return JsonResponse({
                    'html': self.render_selection_html(request),
                    'summary': build_selection_summary(request),
                })
            return redirect('variants:current')

        if action == 'move_up' and problem_id:
            move_problem_in_selection(request, int(problem_id), 'up')
            if is_ajax:
                return JsonResponse({
                    'html': self.render_selection_html(request),
                    'summary': build_selection_summary(request),
                })
            return redirect('variants:current')

        if action == 'move_down' and problem_id:
            move_problem_in_selection(request, int(problem_id), 'down')
            if is_ajax:
                return JsonResponse({
                    'html': self.render_selection_html(request),
                    'summary': build_selection_summary(request),
                })
            return redirect('variants:current')

        if action == 'swap' and problem_id and request.POST.get('target_problem_id'):
            swap_problems_in_selection(
                request,
                int(problem_id),
                int(request.POST.get('target_problem_id')),
            )
            if is_ajax:
                return JsonResponse({
                    'html': self.render_selection_html(request),
                    'summary': build_selection_summary(request),
                })
            return redirect('variants:current')

        if action == 'restore' and problem_id:
            try:
                restore_problem_to_selection(request, int(problem_id))
            except ValidationError as error:
                if is_ajax:
                    return JsonResponse({'error': error.message}, status=400)
                raise
            if is_ajax:
                return JsonResponse({
                    'html': self.render_selection_html(request),
                    'summary': build_selection_summary(request),
                })
            return redirect('variants:current')

        if action == 'restore_all':
            try:
                restore_all_deleted_problems(request)
            except ValidationError as error:
                if is_ajax:
                    return JsonResponse({'error': error.message}, status=400)
                raise
            if is_ajax:
                return JsonResponse({
                    'html': self.render_selection_html(request),
                    'summary': build_selection_summary(request),
                })
            return redirect('variants:current')

        if action == 'clear':
            clear_selection(request)
            if is_ajax:
                return JsonResponse({
                    'html': self.render_selection_html(request),
                    'summary': build_selection_summary(request),
                })
            return redirect('variants:current')

        if action == 'clear_deleted':
            clear_deleted_selection(request)
            if is_ajax:
                return JsonResponse({
                    'html': self.render_selection_html(request),
                    'summary': build_selection_summary(request),
                })
            return redirect('variants:current')

        if action == 'generate':
            form = VariantGenerationForm(
                request.POST,
                request=request,
                is_admin=bool(getattr(request.user, 'is_staff', False)),
            )
            if form.is_valid():
                options = {
                    field_name: form.cleaned_data.get(field_name, False)
                    for field_name in (
                        'is_full',
                        'show_answers',
                        'sort_by_complexity',
                        'sort_by_type',
                        'show_complexity',
                        'show_source',
                        'show_type',
                        'show_max_score',
                        'show_original_number',
                        'show_solution_link',
                        'is_published',
                    )
                }
                existing_variant = None
                if not request.POST.get('force_regenerate'):
                    existing_variant = get_matching_last_generated_variant(
                        request,
                        options=options,
                    )
                if existing_variant is not None:
                    redirect_url = existing_variant.get_absolute_url()
                    if not existing_variant.show_answers:
                        redirect_url = f'{redirect_url}?answers_created=1'
                    return redirect(redirect_url)
                owner = request.user if request.user.is_authenticated else None
                variant = create_variant(
                    problems=get_selection_problems(request),
                    owner=owner,
                    is_full=form.cleaned_data['is_full'],
                    show_answers=form.cleaned_data['show_answers'],
                    sort_by_complexity=form.cleaned_data['sort_by_complexity'],
                    sort_by_type=form.cleaned_data['sort_by_type'],
                    show_complexity=form.cleaned_data['show_complexity'],
                    show_source=form.cleaned_data['show_source'],
                    show_type=form.cleaned_data['show_type'],
                    show_max_score=form.cleaned_data['show_max_score'],
                    show_original_number=form.cleaned_data['show_original_number'],
                    show_solution_link=form.cleaned_data['show_solution_link'],
                    is_published=form.cleaned_data.get('is_published', False),
                )
                set_last_generated_variant_data(request, variant=variant, options=options)
                redirect_url = variant.get_absolute_url()
                if not variant.show_answers:
                    redirect_url = f'{redirect_url}?answers_created=1'
                return redirect(redirect_url)

            return render(
                request,
                self.template_name,
                self.get_context_data(
                    request,
                    form=form,
                ),
            )

        return redirect('variants:current')


class CurrentVariantSelectionDataView(View):
    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return JsonResponse(build_selection_summary(request))


class CurrentVariantSelectionProblemView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Только зарегистрированные пользователи могут собирать варианты.'}, status=403)

        action = request.POST.get('action')
        problem_id = request.POST.get('problem_id')

        if not problem_id:
            return JsonResponse({'error': 'Не передан id задачи.'}, status=400)

        problem = get_object_or_404(Problem, pk=problem_id)

        try:
            if action == 'add':
                add_problem_to_selection(request, problem.id)
            elif action == 'remove':
                remove_problem_from_selection(request, problem.id)
            else:
                return JsonResponse({'error': 'Неизвестное действие.'}, status=400)
        except ValidationError as error:
            return JsonResponse({'error': error.message}, status=400)

        return JsonResponse(build_selection_summary(request))


class CurrentVariantSelectionClearView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Только зарегистрированные пользователи могут собирать варианты.'}, status=403)
        clear_selection(request)
        return JsonResponse(build_selection_summary(request))
