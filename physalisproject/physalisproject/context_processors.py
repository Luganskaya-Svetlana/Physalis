from django.conf import settings
from django.db.models import Q

from accounts.permissions import get_manageable_groups, get_manageable_students
from homework.models import HomeworkSubmission, SubmissionComment


def runtime_flags(request):
    host = request.get_host() if request else ''
    is_local_host = '127.0.0.1' in host or 'localhost' in host
    unread_comment_count = 0
    cabinet_attention_count = 0
    if getattr(request.user, 'is_authenticated', False):
        profile = getattr(request.user, 'profile', None)
        unread_comments = SubmissionComment.objects.exclude(author=request.user).exclude(read_receipts__user=request.user)
        reviewed_count = 0
        if request.user.is_staff:
            unread_comment_count = unread_comments.count()
            pending_count = HomeworkSubmission.objects.filter(
                status__in=[HomeworkSubmission.Status.SUBMITTED, HomeworkSubmission.Status.UNDER_REVIEW]
            ).distinct().count()
        elif profile and profile.can_assign_homework:
            manageable_students = get_manageable_students(request.user)
            manageable_groups = get_manageable_groups(request.user)
            unread_comment_count = unread_comments.filter(
                Q(submission__assignment__created_by=request.user)
                | Q(submission__student__in=manageable_students)
                | Q(submission__assignment__target_groups__in=manageable_groups)
            ).distinct().count()
            pending_count = HomeworkSubmission.objects.filter(
                status__in=[HomeworkSubmission.Status.SUBMITTED, HomeworkSubmission.Status.UNDER_REVIEW]
            ).filter(
                Q(assignment__created_by=request.user)
                | Q(student__in=manageable_students)
                | Q(assignment__target_groups__in=manageable_groups)
            ).distinct().count()
        elif profile and profile.role == profile.Role.STUDENT:
            unread_comment_count = unread_comments.filter(submission__student=request.user).distinct().count()
            pending_count = HomeworkSubmission.objects.filter(
                student=request.user,
                status__in=[
                    HomeworkSubmission.Status.ASSIGNED,
                    HomeworkSubmission.Status.DRAFT,
                    HomeworkSubmission.Status.RETURNED,
                ],
            ).distinct().count()
            reviewed_count = HomeworkSubmission.objects.filter(
                student=request.user,
                status=HomeworkSubmission.Status.REVIEWED,
                reviewed_at__isnull=False,
                student_review_seen_at__isnull=True,
            ).distinct().count()
        else:
            pending_count = 0
        cabinet_attention_count = unread_comment_count + pending_count + reviewed_count

    return {
        'use_dummy_cache': getattr(settings, 'USE_DUMMY_CACHE', False),
        'show_login_link': getattr(settings, 'SHOW_LOGIN_LINK', True) and (
            getattr(settings, 'DEBUG', False) or is_local_host
        ),
        'unread_comment_count': unread_comment_count,
        'cabinet_attention_count': cabinet_attention_count,
    }
