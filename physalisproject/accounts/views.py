from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Case, CharField, IntegerField, OuterRef, Prefetch, Q, Subquery, Value, When
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic.detail import DetailView
import secrets

from accounts.permissions import get_manageable_groups, get_manageable_students
from homework.models import HomeworkAssignment, HomeworkSubmission, SubmissionComment

from .forms import (
    AdminUserEditForm,
    CustomAuthenticationForm,
    ProfileForm,
    SignUpForm,
    TeacherGroupCreateForm,
    TeacherGroupUpdateForm,
    TeacherStudentEditForm,
)
from .models import StudyGroup, UserProfile
from .services import attach_student_to_group


User = get_user_model()


def _russian_count(value, one, few, many):
    remainder_100 = value % 100
    remainder_10 = value % 10
    if 11 <= remainder_100 <= 14:
        form = many
    elif remainder_10 == 1:
        form = one
    elif 2 <= remainder_10 <= 4:
        form = few
    else:
        form = many
    return f'{value} {form}'


def _teacher_scope(request):
    manageable_students = get_manageable_students(request.user)
    manageable_groups = get_manageable_groups(request.user)
    return manageable_students, manageable_groups


def _teacher_unread_comments(request):
    manageable_students, manageable_groups = _teacher_scope(request)
    return (
        SubmissionComment.objects.exclude(author=request.user)
        .exclude(read_receipts__user=request.user)
        .filter(
            Q(submission__assignment__created_by=request.user)
            | Q(submission__student__in=manageable_students)
            | Q(submission__assignment__target_groups__in=manageable_groups)
        )
        .select_related('submission__assignment', 'submission__student', 'author')
        .distinct()
        .order_by('-created_at')
    )


def _teacher_pending_submissions(request):
    manageable_students, manageable_groups = _teacher_scope(request)
    return (
        HomeworkSubmission.objects.filter(
            status__in=[HomeworkSubmission.Status.SUBMITTED, HomeworkSubmission.Status.UNDER_REVIEW]
        )
        .filter(
            Q(assignment__created_by=request.user)
            | Q(student__in=manageable_students)
            | Q(assignment__target_groups__in=manageable_groups)
        )
        .select_related('assignment', 'student')
        .distinct()
        .order_by('-submitted_at')
    )


def _teacher_assignments(request):
    manageable_students, manageable_groups = _teacher_scope(request)
    return (
        HomeworkAssignment.objects.select_related('variant', 'created_by')
        .filter(
            Q(created_by=request.user)
            | Q(target_students__in=manageable_students)
            | Q(target_groups__in=manageable_groups)
        )
        .distinct()
        .order_by('-updated_at')
    )


def _teacher_dashboard_context(request, profile):
    teacher_groups = request.user.managed_study_groups.order_by('name')
    manageable_students = get_manageable_students(request.user)
    unread_comment_links = list(_teacher_unread_comments(request)[:20])
    pending_review_submissions = list(_teacher_pending_submissions(request)[:20])
    for submission in pending_review_submissions:
        if submission.status == HomeworkSubmission.Status.SUBMITTED:
            submission.attention_label = 'ждет проверки'
        elif submission.status == HomeworkSubmission.Status.UNDER_REVIEW:
            submission.attention_label = 'уже проверяется'
        else:
            submission.attention_label = submission.get_status_display()

    tasks_count = _teacher_assignments(request).count()
    pending_count = len(pending_review_submissions)
    messages_count = len(unread_comment_links)
    groups_count = teacher_groups.count()
    students_count = manageable_students.count()
    dashboard_cards = [
        {
            'title': 'Задания',
            'value': tasks_count,
            'description': 'назначенные ДЗ',
            'url': reverse('tasks'),
            'badge': None,
        },
        {
            'title': 'Работы',
            'value': pending_count,
            'description': 'ждут проверки',
            'url': reverse('homework:list'),
            'badge': pending_count or None,
        },
        {
            'title': 'Сообщения',
            'value': messages_count,
            'description': 'непрочитанные комментарии',
            'url': reverse('accounts:messages'),
            'badge': messages_count or None,
        },
        {
            'title': 'Ученики',
            'value': students_count,
            'description': '',
            'meta': _russian_count(groups_count, 'группа', 'группы', 'групп'),
            'url': reverse('accounts:students'),
            'badge': None,
        },
    ]
    if request.user.is_staff:
        total_users = User.objects.count()
        seen_at = profile.admin_users_seen_at
        new_users_count = User.objects.filter(date_joined__gt=seen_at).count() if seen_at else total_users
        dashboard_cards.append(
            {
                'title': 'Пользователи',
                'value': total_users,
                'description': 'всего зарегистрировано',
                'meta': f'новые: {new_users_count}' if new_users_count else None,
                'url': reverse('accounts:users'),
                'badge': new_users_count or None,
            }
        )
    return {
        'profile': profile,
        'title': 'Личный кабинет',
        'dashboard_cards': dashboard_cards,
    }


def _student_dashboard_context(request, profile):
    unread_comment_links = list(
        SubmissionComment.objects.exclude(author=request.user)
        .exclude(read_receipts__user=request.user)
        .filter(submission__student=request.user)
        .select_related('submission__assignment', 'author')
        .distinct()
        .order_by('-created_at')[:10]
    )
    actionable_submissions = list(
        HomeworkSubmission.objects.filter(
            student=request.user,
            status__in=[HomeworkSubmission.Status.ASSIGNED, HomeworkSubmission.Status.DRAFT, HomeworkSubmission.Status.RETURNED],
        )
        .select_related('assignment')
        .order_by('-updated_at')[:10]
    )
    reviewed_unseen_count = HomeworkSubmission.objects.filter(
        student=request.user,
        status=HomeworkSubmission.Status.REVIEWED,
        reviewed_at__isnull=False,
        student_review_seen_at__isnull=True,
    ).count()
    reviewed_count = HomeworkSubmission.objects.filter(
        student=request.user,
        total_score__isnull=False,
    ).count()
    return {
        'profile': profile,
        'title': 'Личный кабинет',
        'dashboard_cards': [
            {
                'title': 'ДЗ',
                'value': len(actionable_submissions),
                'description': 'требуют решения',
                'meta': f'новые проверенные работы: {reviewed_unseen_count}' if reviewed_unseen_count else None,
                'url': reverse('homework:list'),
                'badge': (len(actionable_submissions) + reviewed_unseen_count) or None,
            },
            {
                'title': 'Сообщения',
                'value': len(unread_comment_links),
                'description': 'непрочитанные комментарии',
                'url': reverse('accounts:messages'),
                'badge': len(unread_comment_links) or None,
            },
            {
                'title': 'Статистика',
                'value': reviewed_count,
                'description': 'проверенных работ',
                'url': reverse('accounts:stats'),
                'badge': None,
            },
        ],
    }


class SignUpView(View):
    template_name = 'accounts/signup.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        return render(request, self.template_name, {'form': SignUpForm(), 'title': 'Регистрация'})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:profile')

        form = SignUpForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'title': 'Регистрация'})

        user = form.save()
        invite_token = request.session.pop('pending_group_invite_token', None)
        if invite_token and user.profile.role == user.profile.Role.STUDENT:
            group = StudyGroup.objects.filter(invite_token=invite_token, is_active=True).first()
            if group and attach_student_to_group(user, group):
                messages.success(request, f'Вы привязаны к группе «{group.name}».')
        login(request, user)
        if user.profile.role == user.profile.Role.TEACHER:
            messages.info(
                request,
                'Заявка учителя создана. Доступ к функциям преподавателя появится после одобрения администратором.',
            )
        else:
            messages.success(request, 'Регистрация завершена.')
        return redirect('accounts:profile')


@login_required
def profile_view(request):
    profile = request.user.profile
    if request.user.is_staff or profile.is_teacher_approved:
        return render(
            request,
            'accounts/profile_dashboard.html',
            _teacher_dashboard_context(request, profile),
        )
    return render(request, 'accounts/profile_student_dashboard.html', _student_dashboard_context(request, profile))


@login_required
def profile_edit_view(request):
    profile = request.user.profile
    public_statistics_url = None
    has_statistics = HomeworkSubmission.objects.filter(student=request.user).exists() if profile.role == profile.Role.STUDENT else False
    if profile.role == profile.Role.STUDENT and profile.statistics_share_enabled:
        public_statistics_url = request.build_absolute_uri(
            reverse('accounts:public-stats', kwargs={'token': profile.statistics_share_token})
        )
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлен.')
            return redirect('accounts:profile-edit')
    else:
        form = ProfileForm(instance=profile)
    return render(
        request,
        'accounts/profile_edit.html',
        {
            'form': form,
            'profile': profile,
            'title': 'Личные данные',
            'public_statistics_url': public_statistics_url,
            'has_statistics': has_statistics,
        },
    )


@login_required
def student_stats_view(request):
    profile = request.user.profile
    if profile.role != profile.Role.STUDENT:
        return redirect('accounts:profile')

    return _render_student_stats(request, request.user, title='Моя статистика')


def _render_student_stats(request, student, title):
    submissions = HomeworkSubmission.objects.filter(
        student=student,
    ).select_related('assignment', 'assignment__variant').order_by('-updated_at')
    total_count, submitted_count, average_score_100 = _build_stats_summary(submissions)
    return render(
        request,
        'accounts/student_stats.html',
        {
            'title': title,
            'profile': student.profile,
            'student_obj': student,
            'submissions': submissions,
            'submitted_count': submitted_count,
            'total_count': total_count,
            'average_score_100': average_score_100,
            'is_teacher_view': student.id != request.user.id,
        },
    )


def _build_stats_summary(submissions):
    if hasattr(submissions, 'filter'):
        total_count = submissions.count()
        submitted_count = submissions.filter(submitted_at__isnull=False).count()
        iterable = submissions
    else:
        iterable = list(submissions)
        total_count = len(iterable)
        submitted_count = sum(1 for submission in iterable if submission.submitted_at is not None)
    scored_submissions = [
        submission for submission in iterable
        if submission.total_score is not None and submission.max_score_snapshot
    ]
    average_score_100 = None
    if scored_submissions:
        average_score_100 = round(
            sum(
                float(submission.total_score) / float(submission.max_score_snapshot) * 100
                for submission in scored_submissions
                if float(submission.max_score_snapshot) > 0
            ) / len(scored_submissions)
        )
    return total_count, submitted_count, average_score_100


def _decorate_students_for_table(students):
    students = list(students)
    if not students:
        return students

    student_ids = [student.id for student in students]
    submissions = HomeworkSubmission.objects.filter(student_id__in=student_ids).select_related('student')
    submissions_by_student_id = {}
    for submission in submissions:
        submissions_by_student_id.setdefault(submission.student_id, []).append(submission)

    for student in students:
        student.active_group_names = list(
            student.student_study_groups.filter(is_active=True).order_by('name').values_list('name', flat=True)
        )
        student.total_homework_count, student.submitted_homework_count, student.average_score_100 = _build_stats_summary(
            submissions_by_student_id.get(student.id, [])
        )
    return students


@login_required
def teacher_student_stats_view(request, student_id):
    profile = request.user.profile
    if not (request.user.is_staff or profile.is_teacher_approved):
        return redirect('accounts:profile')

    student = get_object_or_404(
        User.objects.select_related('profile'),
        pk=student_id,
        profile__role=UserProfile.Role.STUDENT,
    )
    if not request.user.is_staff and not get_manageable_students(request.user).filter(pk=student.id).exists():
        return redirect('accounts:profile')

    return _render_student_stats(
        request,
        student,
        title=f'Статистика ученика {student.username}',
    )


@login_required
def admin_users_view(request):
    if not request.user.is_staff:
        return redirect('accounts:profile')

    profile = request.user.profile
    profile.admin_users_seen_at = timezone.now()
    profile.save(update_fields=['admin_users_seen_at'])
    sort = request.GET.get('sort', 'date_joined')
    direction = request.GET.get('dir', 'desc')
    if direction not in {'asc', 'desc'}:
        direction = 'desc'

    primary_group_name = Subquery(
        StudyGroup.objects.filter(is_active=True, students=OuterRef('pk')).order_by('name').values('name')[:1],
        output_field=CharField(),
    )
    users = User.objects.select_related('profile').prefetch_related(
        Prefetch(
            'student_study_groups',
            queryset=StudyGroup.objects.filter(is_active=True).order_by('name'),
        )
    ).annotate(
        primary_group_name=primary_group_name,
        username_sort=Lower('username'),
        role_sort=Case(
            When(is_staff=True, then=Value(0)),
            When(profile__role=UserProfile.Role.TEACHER, then=Value(1)),
            default=Value(2),
            output_field=IntegerField(),
        ),
    )

    sort_fields = {
        'username': ['username_sort', 'id'],
        'first_name': ['first_name', 'id'],
        'last_name': ['last_name', 'id'],
        'role': ['role_sort', 'username', 'id'],
        'group': ['primary_group_name', 'username', 'id'],
        'email': ['email', 'username', 'id'],
        'date_joined': ['date_joined', 'id'],
    }
    if sort not in sort_fields:
        sort = 'date_joined'
    ordering = sort_fields[sort]
    if direction == 'desc':
        ordering = [f'-{field}' for field in ordering]
    users = users.order_by(*ordering)

    sort_columns = [
        {'key': 'username', 'label': 'Логин'},
        {'key': 'first_name', 'label': 'Имя'},
        {'key': 'last_name', 'label': 'Фамилия'},
        {'key': 'role', 'label': 'Роль'},
        {'key': 'group', 'label': 'Группа'},
        {'key': 'email', 'label': 'Почта'},
        {'key': 'date_joined', 'label': 'Зарегистрирован'},
    ]
    for column in sort_columns:
        is_active = column['key'] == sort
        column['is_active'] = is_active
        column['direction'] = direction if is_active else None
        column['next_direction'] = 'asc' if not is_active or direction == 'desc' else 'desc'
    return render(
        request,
        'accounts/users.html',
        {
            'title': 'Пользователи',
            'profile': profile,
            'users': users,
            'sort_columns': sort_columns,
        },
    )


@login_required
def admin_user_edit_view(request, user_id):
    if not request.user.is_staff:
        return redirect('accounts:profile')

    user_obj = get_object_or_404(User.objects.select_related('profile'), pk=user_id)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'delete_user':
            if user_obj.pk == request.user.pk:
                messages.error(request, 'Нельзя удалить самого себя.')
                return redirect('accounts:user-edit', user_id=user_obj.id)
            else:
                user_obj.delete()
                messages.success(request, 'Пользователь удален.')
                return redirect('accounts:users')
        elif action == 'reset_password':
            alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
            temporary_password = ''.join(secrets.choice(alphabet) for _ in range(10))
            user_obj.set_password(temporary_password)
            user_obj.save(update_fields=['password'])
            messages.success(request, f'Временный пароль для {user_obj.username}: {temporary_password}')
            return redirect('accounts:user-edit', user_id=user_obj.id)
        form = AdminUserEditForm(request.POST, instance=user_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Данные пользователя обновлены.')
            return redirect('accounts:users')
    else:
        form = AdminUserEditForm(instance=user_obj)
    return render(
        request,
        'accounts/user_edit.html',
        {
            'title': f'Пользователь {user_obj.username}',
            'profile': request.user.profile,
            'user_obj': user_obj,
            'user_groups': user_obj.student_study_groups.filter(is_active=True).order_by('name'),
            'form': form,
        },
    )


@login_required
def teacher_students_view(request):
    profile = request.user.profile
    if not (request.user.is_staff or profile.is_teacher_approved):
        return redirect('accounts:profile')

    all_teacher_groups = request.user.managed_study_groups.prefetch_related('students').order_by('name')
    teacher_groups = all_teacher_groups.filter(is_active=True)
    hidden_teacher_groups = all_teacher_groups.filter(is_active=False)
    manageable_students = get_manageable_students(request.user).select_related('profile').order_by('username')
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_group':
            group_form = TeacherGroupCreateForm(request.POST, prefix='create', teacher=request.user)
            if group_form.is_valid():
                group_form.save(teacher=request.user)
                messages.success(request, 'Группа создана.')
                return redirect('accounts:students')
        elif action == 'update_group':
            group = get_object_or_404(all_teacher_groups, pk=request.POST.get('group_id'))
            form = TeacherGroupUpdateForm(
                request.POST,
                instance=group,
                prefix=f'group_{group.id}',
                teacher=request.user,
            )
            if form.is_valid():
                form.save(teacher=request.user)
                messages.success(request, 'Группа обновлена.')
                return redirect('accounts:students')
        elif action == 'toggle_group_visibility':
            group = get_object_or_404(all_teacher_groups, pk=request.POST.get('group_id'))
            group.is_active = not group.is_active
            group.save(update_fields=['is_active'])
            messages.success(
                request,
                'Группа восстановлена.' if group.is_active else 'Группа скрыта.',
            )
            return redirect('accounts:students')
    else:
        group_form = TeacherGroupCreateForm(prefix='create', teacher=request.user)

    active_group_forms = [
        (
            group,
            TeacherGroupUpdateForm(
                instance=group,
                prefix=f'group_{group.id}',
                teacher=request.user,
            ),
        )
        for group in teacher_groups
    ]
    hidden_group_forms = [
        (
            group,
            TeacherGroupUpdateForm(
                instance=group,
                prefix=f'group_{group.id}',
                teacher=request.user,
            ),
        )
        for group in hidden_teacher_groups
    ]
    manageable_students = _decorate_students_for_table(manageable_students)
    for group, _form in active_group_forms:
        group.student_table_rows = _decorate_students_for_table(group.students.all())
    for group, _form in hidden_group_forms:
        group.student_table_rows = _decorate_students_for_table(group.students.all())
    ungrouped_students = [student for student in manageable_students if not student.active_group_names]

    return render(
        request,
        'accounts/students.html',
        {
            'title': 'Ученики',
            'profile': profile,
            'group_form': group_form,
            'teacher_groups': teacher_groups,
            'group_forms': active_group_forms,
            'hidden_group_forms': hidden_group_forms,
            'hidden_groups_count': hidden_teacher_groups.count(),
            'manageable_students': manageable_students,
            'ungrouped_students': ungrouped_students,
        },
    )


@login_required
def teacher_groups_view(request):
    return redirect('accounts:students')


@login_required
def teacher_student_edit_view(request, student_id):
    profile = request.user.profile
    if not (request.user.is_staff or profile.is_teacher_approved):
        return redirect('accounts:profile')
    student = get_object_or_404(get_manageable_students(request.user), pk=student_id)
    if request.method == 'POST':
        form = TeacherStudentEditForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, 'Данные ученика обновлены.')
            return redirect('accounts:students')
    else:
        form = TeacherStudentEditForm(instance=student)
    return render(
        request,
        'accounts/student_edit.html',
        {
            'title': f'Ученик {student.username}',
            'profile': profile,
            'student_obj': student,
            'form': form,
        },
    )


@login_required
def unread_messages_view(request):
    profile = request.user.profile
    if request.user.is_staff or profile.is_teacher_approved:
        unread_comment_links = list(_teacher_unread_comments(request))
    else:
        unread_comment_links = list(
            SubmissionComment.objects.exclude(author=request.user)
            .exclude(read_receipts__user=request.user)
            .filter(submission__student=request.user)
            .select_related('submission__assignment', 'submission__student', 'author')
            .distinct()
            .order_by('-created_at')
        )
    return render(
        request,
        'accounts/messages.html',
        {
            'title': 'Сообщения',
            'profile': profile,
            'unread_comment_links': unread_comment_links,
        },
    )


class CustomLoginView(View):
    template_name = 'accounts/login.html'
    authentication_form = CustomAuthenticationForm

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        form = self.authentication_form(request=request)
        return render(request, self.template_name, {'form': form, 'title': 'Вход'})

    def post(self, request):
        if request.user.is_authenticated:
            return redirect('accounts:profile')
        form = self.authentication_form(request=request, data=request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form, 'title': 'Вход'})
        user = form.get_user()
        login(request, user)
        invite_token = request.session.pop('pending_group_invite_token', None)
        if invite_token and hasattr(user, 'profile') and user.profile.role == user.profile.Role.STUDENT:
            group = StudyGroup.objects.filter(invite_token=invite_token, is_active=True).first()
            if group and attach_student_to_group(user, group):
                messages.success(request, f'Вы привязаны к группе «{group.name}».')
        return redirect('accounts:profile')


class GroupInviteView(View):
    def get(self, request, token):
        group = get_object_or_404(StudyGroup, invite_token=token, is_active=True)
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            if not profile or profile.role != profile.Role.STUDENT:
                messages.error(request, 'Привязать к группе можно только аккаунт ученика.')
                return redirect('accounts:profile')
            attach_student_to_group(request.user, group)
            messages.success(request, f'Вы привязаны к группе «{group.name}».')
            return redirect('accounts:profile')

        request.session['pending_group_invite_token'] = str(group.invite_token)
        messages.info(request, f'После входа или регистрации вы будете привязаны к группе «{group.name}».')
        return redirect('accounts:login')


class PublicStudentStatsView(DetailView):
    template_name = 'accounts/public_stats.html'
    context_object_name = 'profile'
    slug_field = 'statistics_share_token'
    slug_url_kwarg = 'token'
    model = UserProfile

    def get_queryset(self):
        return (
            UserProfile.objects.select_related('user')
            .filter(statistics_share_enabled=True, role=UserProfile.Role.STUDENT)
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = context['profile']
        submissions = HomeworkSubmission.objects.filter(
            student=profile.user,
        ).select_related('assignment', 'assignment__variant').order_by('-updated_at')
        total_count, submitted_count, average_score_100 = _build_stats_summary(submissions)
        context['title'] = 'Статистика ученика'
        context['submissions'] = submissions
        context['total_count'] = total_count
        context['submitted_count'] = submitted_count
        context['average_score_100'] = average_score_100
        return context
