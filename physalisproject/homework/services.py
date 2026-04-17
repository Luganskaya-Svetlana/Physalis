from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import (
    HomeworkSubmission,
    HomeworkSubmissionAnswer,
    HomeworkSubmissionSecondPartResponse,
    HomeworkSubmissionSecondPartScore,
    SubmissionAttachment,
    SubmissionComment,
    SubmissionCommentRead,
    SubmissionEvent,
)


UNORDERED_FULL_MATCH_TYPES = {20}
PARTIAL_CREDIT_SET_TYPES = {5, 9, 14, 18}
ORDERED_TWO_DIGIT_PARTIAL_TYPES = {6, 10, 15, 17}


def get_answerable_problems(assignment):
    return [
        problem for problem in assignment.variant.get_problems()
        if getattr(problem, 'type_ege', None) and problem.type_ege.number <= 20
    ]


def get_second_part_problems(assignment):
    answerable_ids = {problem.id for problem in get_answerable_problems(assignment)}
    return [
        problem for problem in assignment.variant.get_problems()
        if problem.id not in answerable_ids
    ]


def ensure_submission_answers(submission):
    existing_ids = set(submission.answers.values_list('problem_id', flat=True))
    answers_to_create = []
    for problem in get_answerable_problems(submission.assignment):
        if problem.id in existing_ids:
            continue
        answers_to_create.append(
            HomeworkSubmissionAnswer(
                submission=submission,
                problem=problem,
                max_score_snapshot=getattr(getattr(problem, 'type_ege', None), 'max_score', None),
            )
        )
    if answers_to_create:
        HomeworkSubmissionAnswer.objects.bulk_create(answers_to_create)


def ensure_second_part_responses(submission):
    existing_ids = set(submission.second_part_responses.values_list('problem_id', flat=True))
    responses_to_create = []
    for problem in get_second_part_problems(submission.assignment):
        if problem.id in existing_ids:
            continue
        responses_to_create.append(
            HomeworkSubmissionSecondPartResponse(
                submission=submission,
                problem=problem,
            )
        )
    if responses_to_create:
        HomeworkSubmissionSecondPartResponse.objects.bulk_create(responses_to_create)


def normalize_decimal_text(value):
    return value.strip().replace(',', '.').replace(' ', '')


def digits_only(value):
    return ''.join(ch for ch in value if ch.isdigit())


def evaluate_answer(problem, raw_value):
    expected = (problem.answer or '').strip()
    given = (raw_value or '').strip()
    max_score = Decimal(str(getattr(getattr(problem, 'type_ege', None), 'max_score', 1) or 1))
    problem_type = getattr(getattr(problem, 'type_ege', None), 'number', None)

    if not given:
        return {
            'normalized_user_answer': '',
            'score_awarded': Decimal('0'),
            'is_correct': False,
            'evaluation_payload': {'mode': 'blank'},
        }

    if problem_type in PARTIAL_CREDIT_SET_TYPES:
        expected_digits = set(digits_only(expected))
        given_digits = set(digits_only(given))
        missing = len(expected_digits - given_digits)
        extra = len(given_digits - expected_digits)
        if missing == 0 and extra == 0:
            score = max_score
            is_correct = True
        elif missing + extra == 1:
            score = Decimal('1')
            is_correct = False
        else:
            score = Decimal('0')
            is_correct = False
        return {
            'normalized_user_answer': ''.join(sorted(given_digits)),
            'score_awarded': min(score, max_score),
            'is_correct': is_correct,
            'evaluation_payload': {
                'mode': 'unordered_set_partial',
                'missing': missing,
                'extra': extra,
            },
        }

    if problem_type in UNORDERED_FULL_MATCH_TYPES:
        expected_digits = ''.join(sorted(digits_only(expected)))
        given_digits = ''.join(sorted(digits_only(given)))
        is_correct = expected_digits == given_digits and bool(expected_digits)
        return {
            'normalized_user_answer': given_digits,
            'score_awarded': max_score if is_correct else Decimal('0'),
            'is_correct': is_correct,
            'evaluation_payload': {'mode': 'unordered_pair'},
        }

    if problem_type in ORDERED_TWO_DIGIT_PARTIAL_TYPES:
        expected_digits = digits_only(expected)
        given_digits = digits_only(given)
        matches = sum(
            1
            for expected_digit, given_digit in zip(expected_digits[:2], given_digits[:2])
            if expected_digit == given_digit
        )
        return {
            'normalized_user_answer': given_digits[:2],
            'score_awarded': Decimal(str(matches)),
            'is_correct': matches == 2,
            'evaluation_payload': {'mode': 'ordered_pair_partial', 'matches': matches},
        }

    normalized_expected = normalize_decimal_text(expected)
    normalized_given = normalize_decimal_text(given)
    is_correct = normalized_expected == normalized_given and bool(normalized_expected)
    return {
        'normalized_user_answer': normalized_given,
        'score_awarded': max_score if is_correct else Decimal('0'),
        'is_correct': is_correct,
        'evaluation_payload': {'mode': 'exact'},
    }


@transaction.atomic
def save_submission_answers(submission, answers_map, actor=None, autosaved=False, mark_as_draft=False):
    ensure_submission_answers(submission)
    changed_problem_ids = []
    for answer in submission.answers.select_related('problem', 'problem__type_ege'):
        raw_value = (answers_map.get(str(answer.problem_id)) or answers_map.get(answer.problem_id) or '').strip()
        if answer.answer_text == raw_value:
            continue
        answer.answer_text = raw_value
        answer.save(update_fields=['answer_text', 'updated_at'])
        changed_problem_ids.append(answer.problem_id)

    if changed_problem_ids:
        submission.last_student_activity_at = timezone.now()
        if submission.status == HomeworkSubmission.Status.ASSIGNED:
            submission.status = HomeworkSubmission.Status.DRAFT
        submission.save(update_fields=['last_student_activity_at', 'status', 'updated_at'])
        SubmissionEvent.objects.create(
            submission=submission,
            actor=actor,
            event_type=(
                SubmissionEvent.EventType.DRAFT_SAVED
                if autosaved or mark_as_draft
                else SubmissionEvent.EventType.EDITED
            ),
            payload={'problem_ids': changed_problem_ids},
        )
    return changed_problem_ids


@transaction.atomic
def submit_submission(submission, actor=None):
    ensure_submission_answers(submission)
    ensure_second_part_responses(submission)
    auto_total = Decimal('0')
    for answer in submission.answers.select_related('problem', 'problem__type_ege'):
        evaluation = evaluate_answer(answer.problem, answer.answer_text)
        answer.normalized_answer = evaluation['normalized_user_answer']
        answer.score_awarded = evaluation['score_awarded']
        answer.is_correct = evaluation['is_correct']
        answer.evaluation_payload = evaluation['evaluation_payload']
        answer.max_score_snapshot = (
            answer.max_score_snapshot
            or getattr(getattr(answer.problem, 'type_ege', None), 'max_score', None)
        )
        answer.save(
            update_fields=[
                'normalized_answer',
                'score_awarded',
                'is_correct',
                'evaluation_payload',
                'max_score_snapshot',
                'updated_at',
            ]
        )
        auto_total += answer.score_awarded or Decimal('0')

    now = timezone.now()
    second_part_problems = get_second_part_problems(submission.assignment)
    has_second_part_files = submission.attachments.exists()
    has_second_part_text = submission.second_part_responses.exclude(text_answer='').exists()
    no_second_part_content = second_part_problems and not has_second_part_files and not has_second_part_text

    submission.submitted_at = now
    submission.auto_score = auto_total
    submission.total_score = auto_total + (submission.manual_score or Decimal('0'))
    submission.last_student_activity_at = now
    if no_second_part_content:
        submission.manual_score = Decimal('0')
        submission.total_score = auto_total
        submission.status = HomeworkSubmission.Status.REVIEWED
        submission.reviewed_at = now
    else:
        submission.status = HomeworkSubmission.Status.SUBMITTED
    submission.save(
        update_fields=[
            'status',
            'submitted_at',
            'auto_score',
            'manual_score',
            'total_score',
            'reviewed_at',
            'last_student_activity_at',
            'updated_at',
        ]
    )
    SubmissionEvent.objects.create(
        submission=submission,
        actor=actor,
        event_type=SubmissionEvent.EventType.SUBMITTED,
        payload={'auto_score': str(auto_total), 'auto_reviewed_without_second_part': no_second_part_content},
    )
    if no_second_part_content:
        SubmissionEvent.objects.create(
            submission=submission,
            actor=actor,
            event_type=SubmissionEvent.EventType.REVIEWED,
            payload={'auto_zero_second_part': True},
        )
    return auto_total


@transaction.atomic
def add_submission_comment(submission, author, body, image=None):
    comment = SubmissionComment.objects.create(
        submission=submission,
        author=author,
        body=body.strip(),
        image=image,
    )
    if author != submission.student and submission.status == HomeworkSubmission.Status.SUBMITTED:
        submission.status = HomeworkSubmission.Status.UNDER_REVIEW
        submission.last_teacher_activity_at = timezone.now()
        submission.save(update_fields=['status', 'last_teacher_activity_at', 'updated_at'])
        SubmissionEvent.objects.create(
            submission=submission,
            actor=author,
            event_type=SubmissionEvent.EventType.REVIEW_STARTED,
            payload={'source': 'comment'},
        )
    event_actor = author
    SubmissionEvent.objects.create(
        submission=submission,
        actor=event_actor,
        event_type=SubmissionEvent.EventType.COMMENT_ADDED,
        payload={'comment_id': comment.id},
    )
    return comment


@transaction.atomic
def delete_submission_comment(comment, actor):
    submission = comment.submission
    comment_id = comment.id
    comment.delete()
    SubmissionEvent.objects.create(
        submission=submission,
        actor=actor,
        event_type=SubmissionEvent.EventType.EDITED,
        payload={'deleted_comment_id': comment_id},
    )


@transaction.atomic
def add_submission_attachments(submission, files, uploaded_by):
    ensure_second_part_responses(submission)
    created = []
    next_order = submission.attachments.count()
    for file_obj in files:
        attachment = SubmissionAttachment.objects.create(
            submission=submission,
            uploaded_by=uploaded_by,
            file=file_obj,
            sort_order=next_order,
        )
        created.append(attachment)
        next_order += 1
    if created:
        submission.last_student_activity_at = timezone.now()
        if submission.status == HomeworkSubmission.Status.ASSIGNED:
            submission.status = HomeworkSubmission.Status.DRAFT
        submission.save(update_fields=['last_student_activity_at', 'status', 'updated_at'])
        SubmissionEvent.objects.create(
            submission=submission,
            actor=uploaded_by,
            event_type=SubmissionEvent.EventType.EDITED,
            payload={'attachment_ids': [attachment.id for attachment in created]},
        )
    return created


@transaction.atomic
def add_submission_attachment_for_problem(submission, problem, files, uploaded_by):
    created = []
    next_order = submission.attachments.filter(problem=problem).count()
    for file_obj in files:
        attachment = SubmissionAttachment.objects.create(
            submission=submission,
            problem=problem,
            uploaded_by=uploaded_by,
            file=file_obj,
            sort_order=next_order,
        )
        created.append(attachment)
        next_order += 1
    if created:
        submission.last_student_activity_at = timezone.now()
        if submission.status == HomeworkSubmission.Status.ASSIGNED:
            submission.status = HomeworkSubmission.Status.DRAFT
        submission.save(update_fields=['last_student_activity_at', 'status', 'updated_at'])
        SubmissionEvent.objects.create(
            submission=submission,
            actor=uploaded_by,
            event_type=SubmissionEvent.EventType.EDITED,
            payload={'attachment_ids': [attachment.id for attachment in created], 'problem_id': problem.id},
        )
    return created


@transaction.atomic
def rotate_submission_attachment(attachment, actor):
    attachment.rotation_degrees = (attachment.rotation_degrees + 90) % 360
    attachment.save(update_fields=['rotation_degrees'])
    now = timezone.now()
    if actor and actor == attachment.submission.student:
        attachment.submission.last_student_activity_at = now
        attachment.submission.save(update_fields=['last_student_activity_at', 'updated_at'])
    else:
        if attachment.submission.status == HomeworkSubmission.Status.SUBMITTED:
            attachment.submission.status = HomeworkSubmission.Status.UNDER_REVIEW
            attachment.submission.last_teacher_activity_at = now
            attachment.submission.save(update_fields=['status', 'last_teacher_activity_at', 'updated_at'])
            SubmissionEvent.objects.create(
                submission=attachment.submission,
                actor=actor,
                event_type=SubmissionEvent.EventType.REVIEW_STARTED,
                payload={'source': 'attachment_rotate'},
            )
        else:
            attachment.submission.last_teacher_activity_at = now
            attachment.submission.save(update_fields=['last_teacher_activity_at', 'updated_at'])
    SubmissionEvent.objects.create(
        submission=attachment.submission,
        actor=actor,
        event_type=SubmissionEvent.EventType.EDITED,
        payload={'attachment_id': attachment.id, 'rotation_degrees': attachment.rotation_degrees},
    )
    return attachment


@transaction.atomic
def delete_submission_attachment(attachment, actor):
    submission = attachment.submission
    attachment_id = attachment.id
    attachment.delete()
    submission.last_student_activity_at = timezone.now()
    submission.save(update_fields=['last_student_activity_at', 'updated_at'])
    SubmissionEvent.objects.create(
        submission=submission,
        actor=actor,
        event_type=SubmissionEvent.EventType.EDITED,
        payload={'deleted_attachment_id': attachment_id},
    )


@transaction.atomic
def review_submission(submission, manual_score=None, actor=None, action='save'):
    now = timezone.now()
    update_fields = ['updated_at', 'last_teacher_activity_at']
    submission.last_teacher_activity_at = now
    if manual_score is not None:
        submission.manual_score = manual_score
        update_fields.append('manual_score')
    submission.total_score = (submission.auto_score or Decimal('0')) + (submission.manual_score or Decimal('0'))
    update_fields.append('total_score')

    if action == 'start_review':
        submission.status = HomeworkSubmission.Status.UNDER_REVIEW
        update_fields.append('status')
        event_type = SubmissionEvent.EventType.REVIEW_STARTED
    elif action == 'return':
        submission.status = HomeworkSubmission.Status.RETURNED
        update_fields.append('status')
        event_type = SubmissionEvent.EventType.STATUS_CHANGED
    elif action == 'reviewed':
        submission.status = HomeworkSubmission.Status.REVIEWED
        submission.reviewed_at = now
        update_fields.extend(['status', 'reviewed_at'])
        event_type = SubmissionEvent.EventType.REVIEWED
    else:
        if submission.status == HomeworkSubmission.Status.SUBMITTED:
            submission.status = HomeworkSubmission.Status.UNDER_REVIEW
            update_fields.append('status')
            event_type = SubmissionEvent.EventType.REVIEW_STARTED
        else:
            event_type = SubmissionEvent.EventType.EDITED

    submission.save(update_fields=update_fields)
    SubmissionEvent.objects.create(
        submission=submission,
        actor=actor,
        event_type=event_type,
        payload={'manual_score': str(submission.manual_score or Decimal('0')), 'action': action},
    )
    return submission


@transaction.atomic
def save_second_part_text_answers(submission, responses_map):
    ensure_second_part_responses(submission)
    changed_problem_ids = []
    for response in submission.second_part_responses.all():
        text_value = (responses_map.get(str(response.problem_id)) or '').strip()
        if response.text_answer == text_value:
            continue
        response.text_answer = text_value
        response.save(update_fields=['text_answer', 'updated_at'])
        changed_problem_ids.append(response.problem_id)
    if changed_problem_ids:
        submission.last_student_activity_at = timezone.now()
        if submission.status == HomeworkSubmission.Status.ASSIGNED:
            submission.status = HomeworkSubmission.Status.DRAFT
        submission.save(update_fields=['last_student_activity_at', 'status', 'updated_at'])
        SubmissionEvent.objects.create(
            submission=submission,
            actor=submission.student,
            event_type=SubmissionEvent.EventType.DRAFT_SAVED,
            payload={'second_part_problem_ids': changed_problem_ids},
        )
    return changed_problem_ids


@transaction.atomic
def save_second_part_scores(submission, scores_map):
    total = Decimal('0')
    saved_any = False
    for problem in get_second_part_problems(submission.assignment):
        raw_value = scores_map.get(str(problem.id), '')
        if raw_value in (None, ''):
            HomeworkSubmissionSecondPartScore.objects.filter(
                submission=submission,
                problem=problem,
            ).delete()
            continue
        score = Decimal(str(raw_value))
        HomeworkSubmissionSecondPartScore.objects.update_or_create(
            submission=submission,
            problem=problem,
            defaults={'score_awarded': score},
        )
        total += score
        saved_any = True
    return total if saved_any else None


def mark_submission_comments_read(submission, user):
    unread_comments = submission.comments.exclude(author=user).exclude(read_receipts__user=user)
    receipts = [
        SubmissionCommentRead(comment=comment, user=user)
        for comment in unread_comments
    ]
    if receipts:
        SubmissionCommentRead.objects.bulk_create(receipts, ignore_conflicts=True)
