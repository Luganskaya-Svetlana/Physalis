from random import choice
from string import ascii_lowercase as letters

from django.core.exceptions import ValidationError

from problems.models import Problem

from .models import Variant


SELECTION_SESSION_KEY = 'current_variant_problem_ids'
DELETED_SELECTION_SESSION_KEY = 'current_variant_deleted_problem_ids'
LAST_GENERATED_VARIANT_SESSION_KEY = 'current_variant_last_generated'
MIN_VARIANT_PROBLEMS = 1
MAX_VARIANT_PROBLEMS = 40
MAX_DELETED_PROBLEMS = 30


def generate_answer_slug():
    return ''.join(choice(letters) for _ in range(4))


def calculate_variant_complexity(problems):
    values = [problem.complexity for problem in problems if problem.complexity is not None]
    if not values:
        return 0
    return round(sum(values) / len(values), 1)


def validate_problem_selection(problem_ids):
    count = len(problem_ids)
    if count < MIN_VARIANT_PROBLEMS:
        raise ValidationError(f'Нужно выбрать хотя бы {MIN_VARIANT_PROBLEMS} задачу.')
    if count > MAX_VARIANT_PROBLEMS:
        raise ValidationError(f'Можно выбрать не более {MAX_VARIANT_PROBLEMS} задач.')


def get_selection_problem_ids(request):
    raw_ids = request.session.get(SELECTION_SESSION_KEY, [])
    result = []
    seen = set()

    for raw_id in raw_ids:
        try:
            problem_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if problem_id in seen:
            continue
        seen.add(problem_id)
        result.append(problem_id)

    return result


def set_selection_problem_ids(request, problem_ids):
    request.session[SELECTION_SESSION_KEY] = [int(problem_id) for problem_id in problem_ids]
    request.session.modified = True


def get_deleted_problem_ids(request):
    raw_ids = request.session.get(DELETED_SELECTION_SESSION_KEY, [])
    result = []
    seen = set()

    for raw_id in raw_ids:
        try:
            problem_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if problem_id in seen:
            continue
        seen.add(problem_id)
        result.append(problem_id)

    return result


def set_deleted_problem_ids(request, problem_ids):
    request.session[DELETED_SELECTION_SESSION_KEY] = [int(problem_id) for problem_id in problem_ids]
    request.session.modified = True


def build_problem_signature(problem_ids):
    return ','.join(str(problem_id) for problem_id in problem_ids)


def normalize_generation_options(options=None):
    options = options or {}
    sort_by_type = bool(options.get('sort_by_type'))
    return {
        'is_full': bool(options.get('is_full')),
        'show_answers': bool(options.get('show_answers')),
        'sort_by_complexity': bool(options.get('sort_by_complexity')) and not bool(options.get('is_full')) and not sort_by_type,
        'sort_by_type': sort_by_type,
        'show_complexity': bool(options.get('show_complexity')),
        'show_source': bool(options.get('show_source')),
        'show_type': bool(options.get('show_type')),
        'show_max_score': bool(options.get('show_max_score')),
        'show_original_number': bool(options.get('show_original_number')),
        'show_solution_link': bool(options.get('show_solution_link')),
        'is_published': bool(options.get('is_published')),
    }


def build_options_signature(options=None):
    normalized = normalize_generation_options(options)
    return '|'.join(
        '1' if normalized[key] else '0'
        for key in (
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
    )


def get_default_generation_options(is_admin=False):
    defaults = normalize_generation_options({})
    if not is_admin:
        defaults.pop('is_published')
    return defaults


def get_current_selection_signature(request):
    return build_problem_signature(get_selection_problem_ids(request))


def get_last_generated_variant_data(request):
    data = request.session.get(LAST_GENERATED_VARIANT_SESSION_KEY, {})
    if not isinstance(data, dict):
        return {}
    return data


def set_last_generated_variant_data(request, *, variant, options):
    request.session[LAST_GENERATED_VARIANT_SESSION_KEY] = {
        'variant_id': variant.id,
        'selection_signature': get_current_selection_signature(request),
        'options': normalize_generation_options(options),
        'options_signature': build_options_signature(options),
    }
    request.session.modified = True


def get_matching_last_generated_variant(request, *, options=None):
    if not request.user.is_authenticated:
        return None

    data = get_last_generated_variant_data(request)
    variant_id = data.get('variant_id')
    if not variant_id:
        return None

    if data.get('selection_signature') != get_current_selection_signature(request):
        return None

    if options is not None and data.get('options_signature') != build_options_signature(options):
        return None

    try:
        variant = Variant.objects.get(pk=variant_id, owner=request.user)
    except Variant.DoesNotExist:
        return None

    return variant


def get_selection_problems(request):
    problem_ids = get_selection_problem_ids(request)
    problems_by_id = (
        Problem.objects
        .select_related('type_ege', 'source')
        .only('id', 'text', 'complexity', 'type_ege__number', 'source__name')
        .in_bulk(problem_ids)
    )
    problems = [problems_by_id[problem_id] for problem_id in problem_ids if problem_id in problems_by_id]

    if len(problems) != len(problem_ids):
        set_selection_problem_ids(request, [problem.id for problem in problems])

    return problems


def get_deleted_selection_problems(request):
    problem_ids = get_deleted_problem_ids(request)
    problems_by_id = (
        Problem.objects
        .select_related('type_ege', 'source')
        .only('id', 'text', 'complexity', 'type_ege__number', 'source__name')
        .in_bulk(problem_ids)
    )
    problems = [problems_by_id[problem_id] for problem_id in problem_ids if problem_id in problems_by_id]

    if len(problems) != len(problem_ids):
        set_deleted_problem_ids(request, [problem.id for problem in problems])

    return problems


def add_problem_to_selection(request, problem_id):
    problem_ids = get_selection_problem_ids(request)
    if problem_id in problem_ids:
        return problem_ids
    if len(problem_ids) >= MAX_VARIANT_PROBLEMS:
        raise ValidationError(f'Можно выбрать не более {MAX_VARIANT_PROBLEMS} задач.')
    problem_ids.append(problem_id)
    set_selection_problem_ids(request, problem_ids)
    set_deleted_problem_ids(
        request,
        [current_id for current_id in get_deleted_problem_ids(request) if current_id != problem_id]
    )
    return problem_ids


def remove_problem_from_selection(request, problem_id):
    problem_ids = [current_id for current_id in get_selection_problem_ids(request) if current_id != problem_id]
    set_selection_problem_ids(request, problem_ids)
    deleted_ids = get_deleted_problem_ids(request)
    if problem_id in deleted_ids:
        deleted_ids = [current_id for current_id in deleted_ids if current_id != problem_id]
    deleted_ids.insert(0, problem_id)
    set_deleted_problem_ids(request, deleted_ids[:MAX_DELETED_PROBLEMS])
    return problem_ids


def restore_problem_to_selection(request, problem_id):
    problem_ids = get_selection_problem_ids(request)
    if problem_id not in problem_ids:
        if len(problem_ids) >= MAX_VARIANT_PROBLEMS:
            raise ValidationError(f'Можно выбрать не более {MAX_VARIANT_PROBLEMS} задач.')
        problem_ids.append(problem_id)
        set_selection_problem_ids(request, problem_ids)

    set_deleted_problem_ids(
        request,
        [current_id for current_id in get_deleted_problem_ids(request) if current_id != problem_id]
    )
    return problem_ids


def clear_selection(request):
    set_selection_problem_ids(request, [])


def clear_deleted_selection(request):
    set_deleted_problem_ids(request, [])


def restore_all_deleted_problems(request):
    problem_ids = get_selection_problem_ids(request)
    deleted_ids = get_deleted_problem_ids(request)
    restored_ids = []

    for problem_id in deleted_ids:
        if problem_id in problem_ids:
            continue
        if len(problem_ids) >= MAX_VARIANT_PROBLEMS:
            break
        problem_ids.append(problem_id)
        restored_ids.append(problem_id)

    if restored_ids:
        set_selection_problem_ids(request, problem_ids)
    set_deleted_problem_ids(request, [problem_id for problem_id in deleted_ids if problem_id not in restored_ids])
    return problem_ids


def move_problem_in_selection(request, problem_id, direction):
    problem_ids = get_selection_problem_ids(request)
    try:
        index = problem_ids.index(problem_id)
    except ValueError:
        return problem_ids

    target_index = index - 1 if direction == 'up' else index + 1
    if target_index < 0 or target_index >= len(problem_ids):
        return problem_ids

    problem_ids[index], problem_ids[target_index] = problem_ids[target_index], problem_ids[index]
    set_selection_problem_ids(request, problem_ids)
    return problem_ids


def swap_problems_in_selection(request, first_problem_id, second_problem_id):
    problem_ids = get_selection_problem_ids(request)
    try:
        first_index = problem_ids.index(first_problem_id)
        second_index = problem_ids.index(second_problem_id)
    except ValueError:
        return problem_ids

    if first_index == second_index:
        return problem_ids

    problem_ids[first_index], problem_ids[second_index] = problem_ids[second_index], problem_ids[first_index]
    set_selection_problem_ids(request, problem_ids)
    return problem_ids


def build_selection_summary(request):
    if not request.user.is_authenticated:
        return {
            'count': 0,
            'problem_ids': [],
            'complexity': 0,
            'can_generate': False,
            'can_use': False,
            'can_open_current': False,
            'deleted_count': 0,
            'max_problems': MAX_VARIANT_PROBLEMS,
            'current_url': '/variants/current/',
        }

    problems = get_selection_problems(request)
    selected_ids = [problem.id for problem in problems]
    deleted_count = len(get_deleted_problem_ids(request))

    return {
        'count': len(problems),
        'problem_ids': selected_ids,
        'complexity': calculate_variant_complexity(problems),
        'can_generate': MIN_VARIANT_PROBLEMS <= len(problems) <= MAX_VARIANT_PROBLEMS,
        'can_use': True,
        'can_open_current': bool(selected_ids or deleted_count),
        'deleted_count': deleted_count,
        'max_problems': MAX_VARIANT_PROBLEMS,
        'current_url': '/variants/current/',
    }


def create_variant(
    *,
    problems,
    is_full,
    show_answers,
    sort_by_complexity,
    sort_by_type=False,
    show_complexity=False,
    show_source=False,
    show_type=False,
    show_max_score=False,
    show_original_number=False,
    show_solution_link=False,
    owner=None,
    is_published=False,
    text=None,
    notes=None,
):
    problem_ids = [problem.id for problem in problems]
    validate_problem_selection(problem_ids)
    if is_full:
        sort_by_complexity = False
    if sort_by_type:
        sort_by_complexity = False

    variant = Variant.objects.create(
        owner=owner,
        text=text,
        notes=notes,
        complexity=calculate_variant_complexity(problems),
        is_full=is_full,
        show_answers=show_answers,
        answer_slug=generate_answer_slug(),
        is_published=is_published,
        sort_by_complexity=sort_by_complexity,
        sort_by_type=sort_by_type,
        show_complexity=show_complexity,
        show_source=show_source,
        show_type=show_type,
        show_max_score=show_max_score,
        show_original_number=show_original_number,
        show_solution_link=show_solution_link,
    )
    variant.problems.set(problem_ids)
    return variant
