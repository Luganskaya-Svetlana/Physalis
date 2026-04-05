import random

from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views import View
from django.views.decorators.cache import cache_page
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from problems.filters import ProblemFilter
from problems.models import Justification, Law, Problem


MAX_GAME_LAWS = 30
MAX_GAME_JUSTIFICATIONS = 20

GAME_SEEN_SESSION_KEY = 'game_seen_ids'
GAME_SOLVED_SESSION_KEY = 'game_solved_ids'
GAME_FILTER_SESSION_KEY = 'game_only_with_justifications'

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


def parse_bool_value(value):
    return str(value).lower() in ('1', 'true', 'on', 'yes')


def get_only_with_justifications(request):
    if 'filter_submitted' in request.GET:
        value = ONLY_WITH_JUSTIFICATIONS_PARAM in request.GET
        request.session[GAME_FILTER_SESSION_KEY] = value
        return value

    if 'filter_submitted' in request.POST:
        value = ONLY_WITH_JUSTIFICATIONS_PARAM in request.POST
        request.session[GAME_FILTER_SESSION_KEY] = value
        return value

    return request.session.get(GAME_FILTER_SESSION_KEY, True)

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
    seen_ids = request.session.get(GAME_SEEN_SESSION_KEY, [])
    if problem_id not in seen_ids:
        seen_ids.append(problem_id)
        request.session[GAME_SEEN_SESSION_KEY] = seen_ids


def remember_solved_game_problem(request, problem_id):
    solved_ids = request.session.get(GAME_SOLVED_SESSION_KEY, [])
    if problem_id not in solved_ids:
        solved_ids.append(problem_id)
        request.session[GAME_SOLVED_SESSION_KEY] = solved_ids


def get_random_game_problem_id(
    request,
    only_with_justifications=True,
    exclude_id=None,
):
    problem_ids = list(
        get_game_queryset(
            only_with_justifications=only_with_justifications
        ).values_list('id', flat=True)
    )
    if not problem_ids:
        raise Http404('Нет задач для тренажёра.')

    seen_ids = request.session.get(GAME_SEEN_SESSION_KEY, [])
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
    request.session[GAME_SEEN_SESSION_KEY] = seen_ids

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


def parse_selected_ids(values):
    return {
        int(value)
        for value in values
        if str(value).isdigit()
    }


def choose_objects_with_limit(all_objects, required_ids, limit, seed):
    required = [obj for obj in all_objects if obj.id in required_ids]
    optional = [obj for obj in all_objects if obj.id not in required_ids]

    if len(required) >= limit:
        result = required[:]
        rnd = random.Random(f'{seed}:required')
        rnd.shuffle(result)
        return result

    rnd = random.Random(f'{seed}:optional')
    rnd.shuffle(optional)

    result = required + optional[:limit - len(required)]

    rnd = random.Random(f'{seed}:final')
    rnd.shuffle(result)
    return result


def get_choice_lists(methods, shuffle_seed):
    correct_law_ids = set()
    correct_justification_ids = set()

    for method in methods:
        correct_law_ids.update(method.laws.values_list('id', flat=True))
        correct_justification_ids.update(
            method.justifications.values_list('id', flat=True)
        )

    all_laws = list(Law.objects.all().order_by('order', 'name'))
    laws = choose_objects_with_limit(
        all_objects=all_laws,
        required_ids=correct_law_ids,
        limit=MAX_GAME_LAWS,
        seed=f'{shuffle_seed}:laws',
    )

    if correct_justification_ids:
        all_justifications = list(
            Justification.objects.all().order_by('order', 'text')
        )
        justifications = choose_objects_with_limit(
            all_objects=all_justifications,
            required_ids=correct_justification_ids,
            limit=MAX_GAME_JUSTIFICATIONS,
            seed=f'{shuffle_seed}:justifications',
        )
    else:
        justifications = []

    return laws, justifications


def build_choice_items(
    objects,
    selected_ids,
    correct_ids,
    extra_ids,
    missing_ids,
    label_attr,
):
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
    exact_law_checks = []
    exact_full = None
    exact_no_justifications = None

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

        check = {
            'method': method,
            'missing_laws': missing_laws,
            'extra_laws': extra_laws,
            'missing_justifications': missing_justifications,
            'extra_justifications': extra_justifications,
            'total_errors': total_errors,
        }
        checks.append(check)

        if method_law_ids == selected_law_ids:
            exact_law_checks.append(check)

            if method_justification_ids == selected_justification_ids:
                exact_full = check

            if not method_justification_ids:
                exact_no_justifications = {
                    'method': method,
                    'missing_laws': set(),
                    'extra_laws': set(),
                    'missing_justifications': set(),
                    'extra_justifications': set(),
                    'total_errors': 0,
                }

    if not checks:
        return None

    if exact_full is not None:
        return {
            'passed': True,
            'best': exact_full,
            'ignored_justifications': False,
        }

    if exact_no_justifications is not None:
        return {
            'passed': True,
            'best': exact_no_justifications,
            'ignored_justifications': bool(selected_justification_ids),
        }

    best_pool = exact_law_checks or checks
    best = min(
        best_pool,
        key=lambda item: (
            item['total_errors'],
            item['method'].order,
            item['method'].id,
        )
    )

    return {
        'passed': False,
        'best': best,
        'ignored_justifications': False,
    }


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


def build_game_progress(request, current_problem_id, only_with_justifications):
    queryset = get_game_queryset(
        only_with_justifications=only_with_justifications
    )
    problem_ids = list(queryset.values_list('id', flat=True))
    allowed_ids = set(problem_ids)

    seen_ids = set(request.session.get(GAME_SEEN_SESSION_KEY, [])) & allowed_ids
    solved_ids = (
        set(request.session.get(GAME_SOLVED_SESSION_KEY, [])) & allowed_ids
    )

    items = []
    for problem_id in problem_ids:
        items.append({
            'id': problem_id,
            'url': reverse('game-detail', kwargs={'pk': problem_id}),
            'is_current': problem_id == current_problem_id,
            'is_seen': problem_id in seen_ids,
            'is_solved': problem_id in solved_ids,
        })

    return {
        'items': items,
        'total_count': len(problem_ids),
        'seen_count': len(seen_ids),
        'solved_count': len(solved_ids),
        'current_problem_is_solved': current_problem_id in solved_ids,
    }


class GameStartView(View):
    def get(self, request):
        only_with_justifications = get_only_with_justifications(request)

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
        return redirect(url)


class ProblemGameView(View):
    template_name = 'problems/problem_game.html'

    def get_problem(self, request, pk):
        only_with_justifications = get_only_with_justifications(request)
        queryset = get_game_queryset(
            only_with_justifications=only_with_justifications
        )
        return queryset.filter(pk=pk).first()

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

    def build_start_redirect(self, request, exclude_id=None):
        url = reverse('game-start')
        if exclude_id is not None:
            return redirect(f'{url}?exclude={exclude_id}')
        return redirect(url)

    def build_context(
        self,
        request,
        problem,
        shuffle_seed=None,
        selected_law_ids=None,
        selected_justification_ids=None,
        evaluation=None,
        revealed=False,
    ):
        only_with_justifications = get_only_with_justifications(request)
        methods = get_active_methods(problem)

        if not methods:
            raise Http404('У этой задачи нет заполненных способов решения.')

        if shuffle_seed is None:
            shuffle_seed = str(random.randint(100000, 999999))

        laws, justifications = get_choice_lists(methods, shuffle_seed)

        selected_law_ids = set(selected_law_ids or [])
        selected_justification_ids = set(selected_justification_ids or [])

        checked = evaluation is not None
        has_result = checked or revealed
        passed = evaluation['passed'] if evaluation is not None else None
        ignored_justifications = (
            evaluation.get('ignored_justifications', False)
            if evaluation is not None else False
        )
        best = evaluation['best'] if evaluation is not None else None

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

        progress = build_game_progress(
            request,
            current_problem_id=problem.id,
            only_with_justifications=only_with_justifications,
        )

        only_with_justifications_count = get_game_queryset(
            only_with_justifications=True
        ).count()
        all_game_problems_count = get_game_queryset(
            only_with_justifications=False
        ).count()

        if revealed:
            result_title = 'Показан один из корректных способов решения.'
            result_box_class = 'result-show'
        elif checked and passed:
            result_title = 'Ответ засчитан.'
            result_box_class = 'result-pass'
        elif checked and not passed:
            result_title = 'Пока не засчитано.'
            result_box_class = 'result-fail'
        else:
            result_title = ''
            result_box_class = ''

        if (passed or revealed) and more_methods_count > 0:
            more_methods_message = other_methods_message(more_methods_count)
        else:
            more_methods_message = ''

        ignored_justifications_message = ''
        if ignored_justifications:
            ignored_justifications_message = (
                'Ответ засчитан по способу решения, для которого '
                'обоснование пока отсутствует. Выбранные пункты '
                'обоснования не учитывались.'
            )

        solution_link_text = (
            'Посмотреть полное решение с обоснованием.'
            if justification_items else
            'Посмотреть полное решение.'
        )

        return {
            'problem': problem,
            'law_items': law_items,
            'justification_items': justification_items,
            'checked': checked,
            'has_result': has_result,
            'passed': passed,
            'revealed': revealed,
            'result_title': result_title,
            'result_box_class': result_box_class,
            'ignored_justifications_message': ignored_justifications_message,
            'more_methods_message': more_methods_message,
            'show_legend': checked and not revealed and not passed,
            'previous_id': previous_id,
            'next_id': next_id,
            'shuffle_seed': shuffle_seed,
            'only_with_justifications': only_with_justifications,
            'only_with_justifications_count': (
                only_with_justifications_count
            ),
            'all_game_problems_count': all_game_problems_count,
            'solution_link_text': solution_link_text,
            'game_problem_items': progress['items'],
            'total_count': progress['total_count'],
            'seen_count': progress['seen_count'],
            'solved_count': progress['solved_count'],
            'current_problem_is_solved': (
                progress['current_problem_is_solved']
            ),
        }

    def build_ajax_payload(self, context):
        return {
            'checked': context['checked'],
            'has_result': context['has_result'],
            'passed': context['passed'],
            'revealed': context['revealed'],
            'result_title': context['result_title'],
            'result_box_class': context['result_box_class'],
            'ignored_justifications_message': (
                context['ignored_justifications_message']
            ),
            'more_methods_message': context['more_methods_message'],
            'show_legend': context['show_legend'],
            'solution_url': context['problem'].get_absolute_url(),
            'solution_link_text': context['solution_link_text'],
            'law_items': [
                {
                    'id': item['id'],
                    'checked': item['checked'],
                    'state': item['state'],
                }
                for item in context['law_items']
            ],
            'justification_items': [
                {
                    'id': item['id'],
                    'checked': item['checked'],
                    'state': item['state'],
                }
                for item in context['justification_items']
            ],
            'solved_count': context['solved_count'],
            'seen_count': context['seen_count'],
            'total_count': context['total_count'],
            'current_problem_id': context['problem'].id,
            'current_problem_is_solved': context['current_problem_is_solved'],
        }

    def get(self, request, pk):
        problem = self.get_problem(request, pk)
        if problem is None:
            return self.build_start_redirect(request, exclude_id=pk)

        remember_game_problem(request, problem.id)
        context = self.build_context(request, problem)
        return render(request, self.template_name, context)

    def post(self, request, pk):
        problem = self.get_problem(request, pk)
        if problem is None:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'redirect_url': reverse('game-start'),
                })
            return self.build_start_redirect(request, exclude_id=pk)

        remember_game_problem(request, problem.id)

        methods = get_active_methods(problem)
        if not methods:
            raise Http404('У этой задачи нет заполненных способов решения.')

        action = request.POST.get('action', 'check')
        shuffle_seed = (
            request.POST.get('shuffle_seed')
            or str(random.randint(100000, 999999))
        )

        evaluation = None
        revealed = False
        selected_law_ids = set()
        selected_justification_ids = set()

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
        else:
            selected_law_ids = parse_selected_ids(
                request.POST.getlist('laws')
            )
            selected_justification_ids = parse_selected_ids(
                request.POST.getlist('justifications')
            )

            evaluation = evaluate_answer(
                methods,
                selected_law_ids,
                selected_justification_ids,
            )

            if evaluation is not None and evaluation['passed']:
                remember_solved_game_problem(request, problem.id)

        context = self.build_context(
            request,
            problem,
            shuffle_seed=shuffle_seed,
            selected_law_ids=selected_law_ids,
            selected_justification_ids=selected_justification_ids,
            evaluation=evaluation,
            revealed=revealed,
        )

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse(self.build_ajax_payload(context))

        return render(request, self.template_name, context)
