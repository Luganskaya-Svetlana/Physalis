import random

from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from problems.filters import ProblemFilter
from problems.models import Justification, Law, Problem


MAX_GAME_LAWS = 30
MAX_GAME_JUSTIFICATIONS = 30
GAME_SESSION_KEY = 'game_seen_ids'
ONLY_WITH_JUSTIFICATIONS_PARAM = 'only_with_justifications'


class ProblemView(DetailView):
    model = Problem
    template_name = 'problems/problem_detail.html'
    context_object_name = 'problem'

    def get_queryset(self):
        return Problem.objects.detail()

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)

        import ziamath
        data['ziamath_version'] = ziamath.__version__

        problem_pk = self.kwargs['pk']

        data['next_problem'] = (
            Problem.objects
            .all()
            .filter(id=int(problem_pk) + 1)
            .exists()
        )
        data['previous_problem'] = (
            Problem.objects
            .all()
            .filter(id=int(problem_pk) - 1)
            .exists()
        )
        return data


class ProblemsView(ListView):
    model = Problem
    template_name = 'problems/problems_list.html'
    context_object_name = 'problems'
    filter = ProblemFilter
    paginate_by = 40

    def get_queryset(self):
        queryset = Problem.objects.list()
        self.filterset = self.filter(self.request.GET, queryset=queryset)
        return self.filterset.qs.order_by('id')

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data['filter'] = ProblemFilter(self.request.GET)
        data['title'] = 'Все задачи'
        return data

    @classmethod
    def as_view(cls, **initkwargs):
        view = super().as_view(**initkwargs)
        view = cache_page(60 * 60)(view)
        return view


def get_only_with_justifications(request):
    value = (
        request.GET.get(ONLY_WITH_JUSTIFICATIONS_PARAM)
        or request.POST.get(ONLY_WITH_JUSTIFICATIONS_PARAM)
    )

    if value is None:
        return True

    return value in ('1', 'true', 'on', 'yes')


def get_game_queryset(only_with_justifications=True):
    queryset = (
        Problem.objects
        .filter(
            solution_methods__is_active=True,
            solution_methods__laws__isnull=False,
        )
        .prefetch_related(
            'solution_methods__laws',
            'solution_methods__justifications',
        )
        .distinct()
        .order_by('id')
    )

    if only_with_justifications:
        queryset = queryset.filter(
            solution_methods__is_active=True,
            solution_methods__justifications__isnull=False,
        ).distinct()

    return queryset


def remember_game_problem(request, problem_id):
    seen_ids = request.session.get(GAME_SESSION_KEY, [])
    if problem_id not in seen_ids:
        seen_ids.append(problem_id)
        request.session[GAME_SESSION_KEY] = seen_ids


def get_random_game_problem_id(request, only_with_justifications=True, exclude_id=None):
    problem_ids = list(
        get_game_queryset(
            only_with_justifications=only_with_justifications
        ).values_list('id', flat=True)
    )
    if not problem_ids:
        raise Http404('Нет задач для тренажёра.')

    seen_ids = request.session.get(GAME_SESSION_KEY, [])
    seen_ids = [pid for pid in seen_ids if pid in problem_ids]

    candidates = [
        pid for pid in problem_ids
        if pid not in seen_ids and pid != exclude_id
    ]

    if not candidates:
        seen_ids = [exclude_id] if exclude_id in problem_ids else []
        candidates = [pid for pid in problem_ids if pid != exclude_id]

    if not candidates:
        candidates = problem_ids[:]

    problem_id = random.choice(candidates)

    if problem_id not in seen_ids:
        seen_ids.append(problem_id)
    request.session[GAME_SESSION_KEY] = seen_ids

    return problem_id


def get_active_methods(problem):
    methods = []
    for method in problem.solution_methods.all():
        if not method.is_active:
            continue

        law_ids = {law.id for law in method.laws.all()}
        if not law_ids:
            continue

        methods.append(method)

    return methods


def limit_choices(all_objects, required_ids, limit):
    required = []
    optional = []

    for obj in all_objects:
        if obj.id in required_ids:
            required.append(obj)
        else:
            optional.append(obj)

    if len(required) >= limit:
        return required

    return required + optional[:limit - len(required)]


def shuffle_objects(objects, seed):
    items = list(objects)
    rnd = random.Random(seed)
    rnd.shuffle(items)
    return items


def get_choice_lists(methods, shuffle_seed):
    correct_law_ids = set()
    correct_justification_ids = set()

    for method in methods:
        correct_law_ids.update(method.laws.values_list('id', flat=True))
        correct_justification_ids.update(
            method.justifications.values_list('id', flat=True)
        )

    all_laws = list(Law.objects.all().order_by('order', 'name'))
    laws = limit_choices(
        all_objects=all_laws,
        required_ids=correct_law_ids,
        limit=MAX_GAME_LAWS,
    )
    laws = shuffle_objects(laws, f'{shuffle_seed}:laws')

    if correct_justification_ids:
        all_justifications = list(
            Justification.objects.all().order_by('order', 'text')
        )
        justifications = limit_choices(
            all_objects=all_justifications,
            required_ids=correct_justification_ids,
            limit=MAX_GAME_JUSTIFICATIONS,
        )
        justifications = shuffle_objects(
            justifications,
            f'{shuffle_seed}:justifications'
        )
    else:
        justifications = []

    return laws, justifications


def build_choice_items(objects, selected_ids, correct_ids, extra_ids, missing_ids, label_attr):
    items = []
    for obj in objects:
        state = ''
        if obj.id in extra_ids:
            state = 'extra'
        elif obj.id in missing_ids:
            state = 'missing'
        elif obj.id in correct_ids and obj.id in selected_ids:
            state = 'correct'
        elif obj.id in selected_ids:
            state = 'selected'

        items.append({
            'id': obj.id,
            'label': getattr(obj, label_attr),
            'checked': obj.id in selected_ids,
            'state': state,
        })
    return items


def evaluate_answer(methods, selected_law_ids, selected_justification_ids):
    checks = []

    for method in methods:
        method_law_ids = {law.id for law in method.laws.all()}
        method_justification_ids = {
            justification.id for justification in method.justifications.all()
        }

        missing_laws = method_law_ids - selected_law_ids
        extra_laws = selected_law_ids - method_law_ids

        missing_justifications = (
            method_justification_ids - selected_justification_ids
        )
        extra_justifications = (
            selected_justification_ids - method_justification_ids
        )

        total_errors = (
            len(missing_laws)
            + len(extra_laws)
            + len(missing_justifications)
            + len(extra_justifications)
        )

        checks.append({
            'method': method,
            'missing_laws': missing_laws,
            'extra_laws': extra_laws,
            'missing_justifications': missing_justifications,
            'extra_justifications': extra_justifications,
            'total_errors': total_errors,
        })

    if not checks:
        return None

    best = min(
        checks,
        key=lambda item: (
            item['total_errors'],
            item['method'].order,
            item['method'].id,
        )
    )
    passed = best['total_errors'] == 0
    return passed, best


def other_methods_message(count):
    if count <= 0:
        return ''

    if count == 1:
        return 'Есть другой способ решения. Попробуете?'

    if count % 10 == 1 and count % 100 != 11:
        word = 'способ'
    elif count % 10 in (2, 3, 4) and count % 100 not in (12, 13, 14):
        word = 'способа'
    else:
        word = 'способов'

    return f'Есть и другие способы решения: ещё {count} {word}.'


class GameStartView(View):
    def get(self, request):
        mode = request.GET.get('mode', 'random')
        if mode not in ('random', 'ordered'):
            mode = 'random'

        only_with_justifications = get_only_with_justifications(request)

        if mode == 'ordered':
            problem_ids = list(
                get_game_queryset(
                    only_with_justifications=only_with_justifications
                ).values_list('id', flat=True)
            )
            if not problem_ids:
                raise Http404('Нет задач для тренажёра.')
            problem_id = problem_ids[0]
        else:
            exclude_id = request.GET.get('exclude')
            exclude_id = (
                int(exclude_id)
                if exclude_id and exclude_id.isdigit()
                else None
            )
            problem_id = get_random_game_problem_id(
                request,
                only_with_justifications=only_with_justifications,
                exclude_id=exclude_id,
            )

        url = reverse('game-detail', kwargs={'pk': problem_id})
        only_with_justifications_value = 1 if only_with_justifications else 0
        return redirect(
            f'{url}?mode={mode}&{ONLY_WITH_JUSTIFICATIONS_PARAM}='
            f'{only_with_justifications_value}'
        )


class ProblemGameView(View):
    template_name = 'problems/problem_game.html'

    def get_problem(self, request, pk):
        only_with_justifications = get_only_with_justifications(request)
        queryset = get_game_queryset(
            only_with_justifications=only_with_justifications
        )
        return queryset.filter(pk=pk).first()

    def get_mode(self, request):
        mode = request.GET.get('mode') or request.POST.get('mode') or 'random'
        if mode not in ('random', 'ordered'):
            mode = 'random'
        return mode

    def get_navigation(self, problem_id, only_with_justifications):
        problem_ids = list(
            get_game_queryset(
                only_with_justifications=only_with_justifications
            ).values_list('id', flat=True)
        )
        previous_id = None
        next_id = None

        if problem_id in problem_ids:
            index = problem_ids.index(problem_id)
            if index > 0:
                previous_id = problem_ids[index - 1]
            if index < len(problem_ids) - 1:
                next_id = problem_ids[index + 1]

        return previous_id, next_id

    def build_context(self, request, problem, checked=False):
        mode = self.get_mode(request)
        only_with_justifications = get_only_with_justifications(request)
        methods = get_active_methods(problem)

        if not methods:
            raise Http404('У этой задачи нет заполненных способов решения.')

        shuffle_seed = (
            request.POST.get('shuffle_seed')
            or request.GET.get('seed')
            or str(random.randint(100000, 999999))
        )

        laws, justifications = get_choice_lists(methods, shuffle_seed)

        selected_law_ids = set()
        selected_justification_ids = set()

        passed = None
        revealed = False
        best = None

        if checked:
            action = request.POST.get('action', 'check')

            if action == 'show':
                revealed = True
                first_method = methods[0]

                selected_law_ids = {
                    law.id for law in first_method.laws.all()
                }
                selected_justification_ids = {
                    justification.id
                    for justification in first_method.justifications.all()
                }

                best = {
                    'method': first_method,
                    'missing_laws': set(),
                    'extra_laws': set(),
                    'missing_justifications': set(),
                    'extra_justifications': set(),
                }
            else:
                selected_law_ids = {
                    int(value)
                    for value in request.POST.getlist('laws')
                    if value.isdigit()
                }
                selected_justification_ids = {
                    int(value)
                    for value in request.POST.getlist('justifications')
                    if value.isdigit()
                }
                result = evaluate_answer(
                    methods,
                    selected_law_ids,
                    selected_justification_ids,
                )
                if result is not None:
                    passed, best = result

        correct_law_ids = set()
        extra_law_ids = set()
        missing_law_ids = set()
        correct_justification_ids = set()
        extra_justification_ids = set()
        missing_justification_ids = set()

        if best is not None:
            correct_law_ids = selected_law_ids - best['extra_laws']
            extra_law_ids = best['extra_laws']
            missing_law_ids = best['missing_laws']

            correct_justification_ids = (
                selected_justification_ids - best['extra_justifications']
            )
            extra_justification_ids = best['extra_justifications']
            missing_justification_ids = best['missing_justifications']

        law_items = build_choice_items(
            objects=laws,
            selected_ids=selected_law_ids,
            correct_ids=correct_law_ids,
            extra_ids=extra_law_ids,
            missing_ids=missing_law_ids,
            label_attr='name',
        )
        justification_items = build_choice_items(
            objects=justifications,
            selected_ids=selected_justification_ids,
            correct_ids=correct_justification_ids,
            extra_ids=extra_justification_ids,
            missing_ids=missing_justification_ids,
            label_attr='text',
        )

        previous_id, next_id = self.get_navigation(
            problem.id,
            only_with_justifications,
        )
        more_methods_count = max(0, len(methods) - 1)

        return {
            'problem': problem,
            'mode': mode,
            'law_items': law_items,
            'justification_items': justification_items,
            'checked': checked,
            'passed': passed,
            'revealed': revealed,
            'more_methods_message': other_methods_message(more_methods_count),
            'previous_id': previous_id,
            'next_id': next_id,
            'shuffle_seed': shuffle_seed,
            'only_with_justifications': only_with_justifications,
        }

    def get(self, request, pk):
        problem = self.get_problem(request, pk)

        if problem is None:
            mode = self.get_mode(request)
            only_with_justifications = get_only_with_justifications(request)
            url = reverse('game-start')
            only_value = 1 if only_with_justifications else 0
            return redirect(
                f'{url}?mode={mode}&{ONLY_WITH_JUSTIFICATIONS_PARAM}={only_value}'
            )

        remember_game_problem(request, problem.id)
        context = self.build_context(request, problem, checked=False)
        return render(request, self.template_name, context)

    def post(self, request, pk):
        problem = self.get_problem(request, pk)

        if problem is None:
            mode = self.get_mode(request)
            only_with_justifications = get_only_with_justifications(request)
            url = reverse('game-start')
            only_value = 1 if only_with_justifications else 0
            return redirect(
                f'{url}?mode={mode}&{ONLY_WITH_JUSTIFICATIONS_PARAM}={only_value}'
            )

        remember_game_problem(request, problem.id)
        context = self.build_context(request, problem, checked=True)
        return render(request, self.template_name, context)
