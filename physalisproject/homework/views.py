from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from accounts.permissions import can_manage_homework, get_manageable_groups, get_manageable_students
from variants.models import Variant

from .forms import HomeworkAssignmentCreateForm, SubmissionCommentForm, SubmissionReviewForm
from .models import HomeworkAssignment, HomeworkSubmission, SubmissionAttachment, SubmissionComment
from .services import (
    add_submission_attachment_for_problem,
    add_submission_attachments,
    add_submission_comment,
    delete_submission_comment,
    delete_submission_attachment,
    ensure_submission_answers,
    ensure_second_part_responses,
    get_answerable_problems,
    get_second_part_problems,
    mark_submission_comments_read,
    review_submission,
    rotate_submission_attachment,
    save_submission_answers,
    save_second_part_scores,
    save_second_part_text_answers,
    submit_submission,
)


def request_user_can_manage_assignment(user, assignment):
    if user.is_staff:
        return True
    if assignment.created_by_id == user.id:
        return True
    manageable_groups = get_manageable_groups(user)
    manageable_students = get_manageable_students(user)
    return assignment.target_groups.filter(id__in=manageable_groups.values('id')).exists() or assignment.target_students.filter(
        id__in=manageable_students.values('id')
    ).exists()


class HomeworkTeacherAccessMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        profile = getattr(request.user, 'profile', None)
        if not (can_manage_homework(request.user) or (profile and profile.role == profile.Role.STUDENT)):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class HomeworkAssignmentCreateView(HomeworkTeacherAccessMixin, View):
    template_name = 'homework/assignment_form.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not can_manage_homework(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_variant(self):
        return get_object_or_404(Variant.objects.detail(), pk=self.kwargs['variant_id'])

    def get(self, request, *args, **kwargs):
        variant = self.get_variant()
        form = HomeworkAssignmentCreateForm(request=request, variant=variant)
        return render(
            request,
            self.template_name,
            {
                'form': form,
                'variant': variant,
                'title': 'Назначить ДЗ',
                'manageable_students': get_manageable_students(request.user),
                'manageable_groups': get_manageable_groups(request.user),
            },
        )

    def post(self, request, *args, **kwargs):
        variant = self.get_variant()
        form = HomeworkAssignmentCreateForm(request.POST, request=request, variant=variant)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    'form': form,
                    'variant': variant,
                    'title': 'Назначить ДЗ',
                    'manageable_students': get_manageable_students(request.user),
                    'manageable_groups': get_manageable_groups(request.user),
                },
            )

        assignment = form.save()
        return redirect('homework:detail', pk=assignment.pk)


class HomeworkAssignmentUpdateView(HomeworkTeacherAccessMixin, View):
    template_name = 'homework/assignment_form.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not can_manage_homework(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_assignment(self):
        assignment = get_object_or_404(
            HomeworkAssignment.objects.select_related('variant', 'created_by').prefetch_related('submissions'),
            pk=self.kwargs['pk'],
        )
        if not request_user_can_manage_assignment(self.request.user, assignment):
            raise PermissionDenied
        return assignment

    def build_form(self, request, assignment, data=None):
        started_exists = assignment.submissions.exclude(status=HomeworkSubmission.Status.ASSIGNED).exists()
        return HomeworkAssignmentCreateForm(
            data=data,
            instance=assignment,
            request=request,
            variant=assignment.variant,
            allow_retarget=not started_exists,
        )

    def get(self, request, *args, **kwargs):
        assignment = self.get_assignment()
        form = self.build_form(request, assignment)
        return render(
            request,
            self.template_name,
            {
                'form': form,
                'variant': assignment.variant,
                'assignment': assignment,
                'title': 'Редактировать ДЗ',
                'manageable_students': get_manageable_students(request.user),
                'manageable_groups': get_manageable_groups(request.user),
                'is_edit': True,
            },
        )

    def post(self, request, *args, **kwargs):
        assignment = self.get_assignment()
        if request.POST.get('action') == 'delete_assignment':
            assignment.delete()
            return redirect('tasks')
        old_resolved_max_score = assignment.get_resolved_max_score()
        form = self.build_form(request, assignment, data=request.POST)
        if not form.is_valid():
            return render(
                request,
                self.template_name,
                {
                    'form': form,
                    'variant': assignment.variant,
                    'assignment': assignment,
                    'title': 'Редактировать ДЗ',
                    'manageable_students': get_manageable_students(request.user),
                    'manageable_groups': get_manageable_groups(request.user),
                    'is_edit': True,
                },
            )
        assignment = form.save()
        new_resolved_max_score = assignment.get_resolved_max_score()
        if old_resolved_max_score != new_resolved_max_score:
            assignment.submissions.filter(status=HomeworkSubmission.Status.ASSIGNED).update(
                max_score_snapshot=new_resolved_max_score,
            )
        return redirect('homework:detail', pk=assignment.pk)


class HomeworkAssignmentQuerysetMixin:
    def get_queryset(self):
        queryset = HomeworkAssignment.objects.select_related('variant', 'created_by').prefetch_related(
            'target_students',
            'target_groups',
            'target_groups__teachers',
            Prefetch(
                'submissions',
                queryset=HomeworkSubmission.objects.select_related('student', 'assignment').prefetch_related(
                    'attachments',
                    'comments__author',
                    'comments__read_receipts',
                    'answers__problem__type_ege',
                    'second_part_responses__problem__type_ege',
                    'second_part_scores__problem__type_ege',
                    'events',
                ),
            ),
        )
        user = self.request.user
        if user.is_staff:
            return queryset.distinct()
        profile = getattr(user, 'profile', None)
        if profile and profile.role == profile.Role.STUDENT:
            return queryset.filter(submissions__student=user).distinct()

        manageable_students = get_manageable_students(user)
        manageable_groups = get_manageable_groups(user)
        return queryset.filter(
            Q(created_by=user)
            | Q(target_students__in=manageable_students)
            | Q(target_groups__in=manageable_groups)
        ).distinct()


class HomeworkAssignmentListView(HomeworkTeacherAccessMixin, HomeworkAssignmentQuerysetMixin, ListView):
    template_name = 'homework/assignment_list.html'
    context_object_name = 'assignments'
    paginate_by = 30

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = getattr(self.request.user, 'profile', None)
        context['title'] = 'Домашние задания'
        context['is_student_view'] = bool(profile and profile.role == profile.Role.STUDENT)
        if context['is_student_view']:
            for assignment in context['assignments']:
                assignment.student_submission = next(
                    (
                        submission
                        for submission in assignment.submissions.all()
                        if submission.student_id == self.request.user.id
                    ),
                    None,
                )
                assignment.pending_review_count = 0
                assignment.student_has_total_score = (
                    assignment.student_submission is not None
                    and assignment.student_submission.total_score is not None
                )
        else:
            for assignment in context['assignments']:
                assignment.pending_review_count = sum(
                    1 for submission in assignment.submissions.all()
                    if submission.teacher_needs_review
                )
            context['assignments'] = sorted(
                context['assignments'],
                key=lambda assignment: (-assignment.pending_review_count, assignment.id),
            )
        return context


class HomeworkTeacherTaskListView(HomeworkTeacherAccessMixin, HomeworkAssignmentQuerysetMixin, ListView):
    template_name = 'homework/task_list.html'
    context_object_name = 'assignments'
    paginate_by = 50

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if not can_manage_homework(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for assignment in context['assignments']:
            assignment.assigned_students_count = assignment.get_effective_students().count()
            assignment.submitted_students_count = sum(
                1 for submission in assignment.submissions.all()
                if submission.submitted_at is not None
            )
        context['title'] = 'Задания'
        return context


class HomeworkSubmissionListView(HomeworkTeacherAccessMixin, ListView):
    template_name = 'homework/submission_list.html'
    context_object_name = 'submissions'
    paginate_by = 50

    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, 'profile', None)
        if profile and profile.role == profile.Role.STUDENT:
            assignments = HomeworkAssignmentQuerysetMixin()
            assignments.request = self.request
            self.student_assignments = HomeworkAssignmentQuerysetMixin.get_queryset(assignments)
            return HomeworkSubmission.objects.none()

        if not can_manage_homework(user):
            raise PermissionDenied

        queryset = HomeworkSubmission.objects.select_related(
            'student',
            'assignment',
            'assignment__variant',
        ).prefetch_related('events').filter(submitted_at__isnull=False)
        if user.is_staff:
            return queryset.order_by('-submitted_at', '-id')

        manageable_students = get_manageable_students(user)
        manageable_groups = get_manageable_groups(user)
        return queryset.filter(
            Q(assignment__created_by=user)
            | Q(student__in=manageable_students)
            | Q(assignment__target_groups__in=manageable_groups)
        ).distinct().order_by('-submitted_at', '-id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        profile = getattr(self.request.user, 'profile', None)
        is_student_view = bool(profile and profile.role == profile.Role.STUDENT)
        context['title'] = 'Работы'
        context['is_student_view'] = is_student_view
        if is_student_view:
            assignments = getattr(self, 'student_assignments', [])
            for assignment in assignments:
                assignment.student_submission = next(
                    (
                        submission
                        for submission in assignment.submissions.all()
                        if submission.student_id == self.request.user.id
                    ),
                    None,
                )
                assignment.student_has_total_score = (
                    assignment.student_submission is not None
                    and assignment.student_submission.total_score is not None
                )
            context['assignments'] = assignments
        else:
            for submission in context['submissions']:
                submission_count = sum(
                    1
                    for event in submission.events.all()
                    if event.event_type == event.EventType.SUBMITTED
                )
                if submission.status == submission.Status.SUBMITTED:
                    submission.list_status_label = 'сдана'
                elif submission.status == submission.Status.UNDER_REVIEW:
                    submission.list_status_label = 'проверяется'
                elif submission.status == submission.Status.REVIEWED:
                    submission.list_status_label = 'проверена'
                else:
                    submission.list_status_label = submission.get_status_display()
                if submission_count > 1:
                    submission.list_status_label = f'{submission.list_status_label} ({submission_count} раз)'
        return context


class HomeworkAssignmentDetailView(HomeworkTeacherAccessMixin, HomeworkAssignmentQuerysetMixin, DetailView):
    template_name = 'homework/assignment_detail.html'
    context_object_name = 'assignment'

    @staticmethod
    def get_answer_state(answer):
        if answer is None or not (answer.answer_text or '').strip():
            return ''
        max_score = answer.max_score_snapshot or 0
        score = answer.score_awarded or 0
        if score <= 0:
            return 'wrong'
        if max_score and score >= max_score:
            return 'correct'
        return 'partial'

    @staticmethod
    def get_second_part_max_score(problem):
        return getattr(getattr(problem, 'type_ege', None), 'max_score', None)

    @staticmethod
    def get_problem_label(problem, index):
        number = getattr(getattr(problem, 'type_ege', None), 'number', None)
        return number or index

    def build_second_part_context(self, assignment, submission):
        variant_positions = {
            problem.id: index
            for index, problem in enumerate(assignment.variant.get_problems(), start=1)
        }
        response_map = {
            response.problem_id: response
            for response in submission.second_part_responses.all()
        }
        score_map = {
            score.problem_id: score
            for score in submission.second_part_scores.all()
        }
        items = []
        total_score = 0
        total_max_score = 0
        has_full_max_score = True
        for index, problem in enumerate(get_second_part_problems(assignment), start=1):
            max_score = self.get_second_part_max_score(problem)
            score = score_map.get(problem.id)
            if score is not None and score.score_awarded is not None:
                total_score += score.score_awarded
            if max_score is None:
                has_full_max_score = False
            else:
                total_max_score += max_score
            items.append(
                {
                    'problem': problem,
                    'response': response_map.get(problem.id),
                    'attachments': [attachment for attachment in submission.attachments.all() if attachment.problem_id == problem.id],
                    'score': score,
                    'max_score': max_score,
                    'display_number': variant_positions.get(problem.id, index),
                }
            )
        return {
            'items': items,
            'shared_attachments': [attachment for attachment in submission.attachments.all() if attachment.problem_id is None],
            'total_score': total_score,
            'total_max_score': total_max_score if has_full_max_score else None,
        }

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        assignment = self.object
        profile = getattr(request.user, 'profile', None)
        is_student_view = bool(profile and profile.role == profile.Role.STUDENT)
        action = request.POST.get('action')
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
        if is_student_view:
            submission = assignment.submissions.filter(student=request.user).first()
            if submission is None:
                raise PermissionDenied
            if action in {'save_draft', 'submit'}:
                if not submission.can_student_edit:
                    raise PermissionDenied
                answers_map = {
                    key.removeprefix('answer_'): value
                    for key, value in request.POST.items()
                    if key.startswith('answer_')
                }
                save_submission_answers(
                    submission,
                    answers_map,
                    actor=request.user,
                    autosaved=False,
                    mark_as_draft=(action == 'save_draft'),
                )
                responses_map = {
                    key.removeprefix('second_part_text_'): value
                    for key, value in request.POST.items()
                    if key.startswith('second_part_text_')
                }
                if submission.assignment.allow_second_part_text:
                    save_second_part_text_answers(submission, responses_map)
                if action == 'submit':
                    submit_submission(submission, actor=request.user)
            elif action == 'upload_attachments':
                if not submission.can_student_edit:
                    raise PermissionDenied
                files = request.FILES.getlist('attachments')
                if files:
                    created = add_submission_attachments(submission, files, request.user)
                    if is_ajax:
                        return JsonResponse(
                            {
                                'ok': True,
                                'attachments': [
                                    {
                                        'id': attachment.id,
                                        'is_image': attachment.is_image,
                                        'file_url': attachment.file.url,
                                        'viewer_url': self.request.build_absolute_uri(
                                            reverse('homework:attachment-detail', kwargs={'pk': attachment.id})
                                        ),
                                        'rotation_degrees': attachment.rotation_degrees,
                                    }
                                    for attachment in created
                                ],
                            }
                        )
            elif action == 'upload_problem_attachments':
                if not submission.can_student_edit:
                    raise PermissionDenied
                problem = get_object_or_404(
                    assignment.variant.problems.all(),
                    pk=request.POST.get('problem_id'),
                )
                files = request.FILES.getlist('attachments')
                if files:
                    created = add_submission_attachment_for_problem(submission, problem, files, request.user)
                    if is_ajax:
                        return JsonResponse(
                            {
                                'ok': True,
                                'attachments': [
                                    {
                                        'id': attachment.id,
                                        'is_image': attachment.is_image,
                                        'file_url': attachment.file.url,
                                        'viewer_url': self.request.build_absolute_uri(
                                            reverse('homework:attachment-detail', kwargs={'pk': attachment.id})
                                        ),
                                        'rotation_degrees': attachment.rotation_degrees,
                                    }
                                    for attachment in created
                                ],
                            }
                        )
            elif action == 'rotate_attachment':
                attachment = get_object_or_404(SubmissionAttachment, pk=request.POST.get('attachment_id'), submission=submission)
                if not submission.can_student_edit or not attachment.is_image:
                    raise PermissionDenied
                rotate_submission_attachment(attachment, request.user)
                if is_ajax:
                    return JsonResponse({'ok': True, 'rotation_degrees': attachment.rotation_degrees})
            elif action == 'delete_attachment':
                attachment = get_object_or_404(SubmissionAttachment, pk=request.POST.get('attachment_id'), submission=submission)
                if not submission.can_student_edit:
                    raise PermissionDenied
                delete_submission_attachment(attachment, request.user)
                if is_ajax:
                    return JsonResponse({'ok': True, 'deleted': True})
            elif action == 'add_comment':
                form = SubmissionCommentForm(request.POST, request.FILES)
                if form.is_valid():
                    add_submission_comment(
                        submission,
                        request.user,
                        form.cleaned_data['body'],
                        image=form.cleaned_data.get('image'),
                    )
            elif action == 'delete_comment':
                comment = get_object_or_404(SubmissionComment, pk=request.POST.get('comment_id'), submission=submission)
                if comment.author_id != request.user.id:
                    raise PermissionDenied
                delete_submission_comment(comment, request.user)
            else:
                raise PermissionDenied
        else:
            if not can_manage_homework(request.user):
                raise PermissionDenied
            submission = get_object_or_404(
                assignment.submissions.select_related('student'),
                pk=request.POST.get('submission_id'),
            )
            if action == 'teacher_comment':
                form = SubmissionCommentForm(request.POST, request.FILES)
                if form.is_valid():
                    add_submission_comment(
                        submission,
                        request.user,
                        form.cleaned_data['body'],
                        image=form.cleaned_data.get('image'),
                    )
                    has_review_payload = (
                        'manual_score' in request.POST
                        or any(key.startswith('problem_score_') for key in request.POST.keys())
                    )
                    if has_review_payload:
                        review_form = SubmissionReviewForm(request.POST, instance=submission)
                        if review_form.is_valid():
                            reviewed_submission = review_form.save(commit=False)
                            second_part_scores = save_second_part_scores(
                                submission,
                                {
                                    key.removeprefix('problem_score_'): value
                                    for key, value in request.POST.items()
                                    if key.startswith('problem_score_')
                                },
                            )
                            manual_score = (
                                second_part_scores
                                if second_part_scores is not None
                                else reviewed_submission.manual_score
                            )
                            review_submission(
                                submission,
                                manual_score=manual_score,
                                actor=request.user,
                                action='save',
                            )
            elif action == 'delete_comment':
                comment = get_object_or_404(SubmissionComment, pk=request.POST.get('comment_id'), submission=submission)
                if comment.author_id != request.user.id:
                    raise PermissionDenied
                delete_submission_comment(comment, request.user)
            elif action == 'teacher_rotate_attachment':
                attachment = get_object_or_404(SubmissionAttachment, pk=request.POST.get('attachment_id'), submission=submission)
                if not attachment.is_image:
                    raise PermissionDenied
                rotate_submission_attachment(attachment, request.user)
                if is_ajax:
                    return JsonResponse({'ok': True, 'rotation_degrees': attachment.rotation_degrees})
            elif action in {'start_review', 'return_submission', 'mark_reviewed', 'save_review'}:
                form = SubmissionReviewForm(request.POST, instance=submission)
                if form.is_valid():
                    reviewed_submission = form.save(commit=False)
                    second_part_scores = save_second_part_scores(
                        submission,
                        {
                            key.removeprefix('problem_score_'): value
                            for key, value in request.POST.items()
                            if key.startswith('problem_score_')
                        },
                    )
                    manual_score = second_part_scores if second_part_scores is not None else reviewed_submission.manual_score
                    review_action = {
                        'start_review': 'start_review',
                        'return_submission': 'return',
                        'mark_reviewed': 'reviewed',
                        'save_review': 'save',
                    }[action]
                    review_submission(
                        submission,
                        manual_score=manual_score,
                        actor=request.user,
                        action=review_action,
                    )
            else:
                raise PermissionDenied
        if not is_student_view and submission is not None:
            return redirect(f"{assignment.get_absolute_url()}?submission={submission.id}")
        return redirect('homework:detail', pk=assignment.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assignment = context['assignment']
        profile = getattr(self.request.user, 'profile', None)
        is_student_view = bool(profile and profile.role == profile.Role.STUDENT)
        context['title'] = assignment.title or f'ДЗ #{assignment.pk}'
        context['assignment_title_is_default_variant'] = assignment.title == f'ДЗ по варианту #{assignment.variant_id}'
        context['resolved_max_score'] = assignment.get_resolved_max_score()
        context['effective_students'] = assignment.get_effective_students()
        context['is_student_view'] = is_student_view
        context['has_second_part'] = bool(get_second_part_problems(assignment))
        context['show_second_part_meta'] = context['has_second_part']
        context['allow_shared_second_part_uploads'] = assignment.allows_shared_second_part_uploads
        context['allow_per_problem_second_part_uploads'] = assignment.allows_per_problem_second_part_uploads
        context['current_year'] = timezone.localdate().year
        if is_student_view:
            submission = assignment.submissions.filter(student=self.request.user).first()
            context['student_submission'] = submission
            context['comment_form'] = SubmissionCommentForm()
            if submission is not None:
                ensure_submission_answers(submission)
                ensure_second_part_responses(submission)
                mark_submission_comments_read(submission, self.request.user)
                answer_map = {answer.problem_id: answer for answer in submission.answers.all()}
                second_part_response_map = {
                    response.problem_id: response
                    for response in submission.second_part_responses.all()
                }
                context['answerable_problems'] = [
                    {
                        'problem': problem,
                        'answer': answer_map.get(problem.id),
                        'answer_state': self.get_answer_state(answer_map.get(problem.id)),
                    }
                    for problem in get_answerable_problems(assignment)
                ]
                context['first_part_max_score'] = sum(
                    (
                        getattr(getattr(item['problem'], 'type_ege', None), 'max_score', None)
                        or (item['answer'].max_score_snapshot if item['answer'] else 0)
                        or 0
                    )
                    for item in context['answerable_problems']
                )
                second_part_context = self.build_second_part_context(assignment, submission)
                context['second_part_problems'] = second_part_context['items']
                context['shared_second_part_attachments'] = second_part_context['shared_attachments']
                context['second_part_total_score'] = second_part_context['total_score']
                context['second_part_total_max_score'] = second_part_context['total_max_score']
                context['student_submission_has_manual_score'] = submission.manual_score is not None
                context['student_submission_is_submitted'] = submission.status != submission.Status.ASSIGNED
        else:
            selected_submission_id = self.request.GET.get('submission')
            detailed_submissions = []
            for submission in assignment.submissions.all():
                ensure_submission_answers(submission)
                ensure_second_part_responses(submission)
                mark_submission_comments_read(submission, self.request.user)
                answer_map = {answer.problem_id: answer for answer in submission.answers.all()}
                second_part_context = self.build_second_part_context(assignment, submission)
                submission_item = {
                    'submission': submission,
                    'answerable_problems': [
                        {
                            'problem': problem,
                            'answer': answer_map.get(problem.id),
                            'answer_state': self.get_answer_state(answer_map.get(problem.id)),
                        }
                        for problem in get_answerable_problems(assignment)
                    ],
                    'second_part_problems': second_part_context['items'],
                    'shared_second_part_attachments': second_part_context['shared_attachments'],
                    'second_part_total_score': second_part_context['total_score'],
                    'second_part_total_max_score': second_part_context['total_max_score'],
                    'review_form': SubmissionReviewForm(instance=submission),
                    'comment_form': SubmissionCommentForm(),
                    'pending_review': submission.teacher_needs_review,
                    'has_manual_score': submission.manual_score is not None,
                    'per_problem_scores_present': second_part_context['items'] and any(
                        second_item['score'] is not None
                        for second_item in second_part_context['items']
                    ),
                    'manual_score_overrides_problem_scores': (
                        submission.manual_score is not None
                        and any(second_item['score'] is not None for second_item in second_part_context['items'])
                        and submission.manual_score != second_part_context['total_score']
                    ),
                    'auto_zero_second_part': submission.events.filter(
                        event_type='reviewed',
                        payload__auto_zero_second_part=True,
                    ).exists(),
                }
                submission_item['first_part_max_score'] = sum(
                    (
                        getattr(getattr(answer_item['problem'], 'type_ege', None), 'max_score', None)
                        or (answer_item['answer'].max_score_snapshot if answer_item['answer'] else 0)
                        or 0
                    )
                    for answer_item in submission_item['answerable_problems']
                )
                detailed_submissions.append(submission_item)
            sorted_submissions = sorted(
                detailed_submissions,
                key=lambda item: (not item['pending_review'], item['submission'].student.username),
            )
            for item in sorted_submissions:
                submission = item['submission']
                if submission.status == submission.Status.SUBMITTED:
                    item['summary_status_label'] = 'сдана'
                    item['summary_status_class'] = 'submitted'
                elif submission.status == submission.Status.UNDER_REVIEW:
                    item['summary_status_label'] = 'проверяется'
                    item['summary_status_class'] = 'reviewing'
                elif submission.status == submission.Status.REVIEWED:
                    item['summary_status_label'] = 'проверена'
                    item['summary_status_class'] = 'reviewed'
                else:
                    item['summary_status_label'] = submission.get_status_display()
                    item['summary_status_class'] = 'default'
            context['selected_submission_id'] = int(selected_submission_id) if selected_submission_id and selected_submission_id.isdigit() else None
            if context['selected_submission_id']:
                context['detailed_submissions'] = [
                    item for item in sorted_submissions
                    if item['submission'].id == context['selected_submission_id']
                ]
            else:
                context['detailed_submissions'] = []
            context['teacher_submission_summaries'] = sorted_submissions
        return context


class HomeworkSubmissionAutosaveView(HomeworkTeacherAccessMixin, HomeworkAssignmentQuerysetMixin, View):
    def post(self, request, *args, **kwargs):
        assignment = get_object_or_404(self.get_queryset(), pk=kwargs['pk'])
        profile = getattr(request.user, 'profile', None)
        if not (profile and profile.role == profile.Role.STUDENT):
            raise PermissionDenied

        submission = assignment.submissions.filter(student=request.user).first()
        if submission is None or not submission.can_student_edit:
            raise PermissionDenied

        answers_map = {}
        for key, value in request.POST.items():
            if key.startswith('answer_'):
                answers_map[key.removeprefix('answer_')] = value
        responses_map = {}
        for key, value in request.POST.items():
            if key.startswith('second_part_text_'):
                responses_map[key.removeprefix('second_part_text_')] = value

        changed_problem_ids = save_submission_answers(
            submission,
            answers_map,
            actor=request.user,
            autosaved=True,
        )
        changed_second_part_problem_ids = save_second_part_text_answers(submission, responses_map)
        return JsonResponse({
            'saved': True,
            'status': submission.get_status_display(),
            'changed_problem_ids': changed_problem_ids,
            'changed_second_part_problem_ids': changed_second_part_problem_ids,
        })


class HomeworkAttachmentDetailView(HomeworkTeacherAccessMixin, View):
    template_name = 'homework/attachment_detail.html'

    def get_attachment(self):
        attachment = get_object_or_404(
            SubmissionAttachment.objects.select_related(
                'submission',
                'submission__assignment',
                'submission__student',
                'submission__assignment__variant',
            ),
            pk=self.kwargs['pk'],
        )
        submission = attachment.submission
        assignment = submission.assignment
        profile = getattr(self.request.user, 'profile', None)
        is_student_view = bool(profile and profile.role == profile.Role.STUDENT)
        if is_student_view:
            if submission.student_id != self.request.user.id:
                raise PermissionDenied
        elif not (can_manage_homework(self.request.user) and request_user_can_manage_assignment(self.request.user, assignment)):
            raise PermissionDenied
        return attachment

    def get(self, request, *args, **kwargs):
        attachment = self.get_attachment()
        return render(
            request,
            self.template_name,
            {
                'attachment': attachment,
                'submission': attachment.submission,
                'assignment': attachment.submission.assignment,
                'title': f'Вложение #{attachment.pk}',
            },
        )
