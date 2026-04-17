from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from problems.models import PartOfEGE, Problem, Source, TypeInEGE
from variants.models import Variant
from accounts.models import TeacherStudentLink
from homework.models import (
    HomeworkAssignment,
    HomeworkSubmission,
    HomeworkSubmissionAnswer,
    HomeworkSubmissionSecondPartScore,
    SubmissionAttachment,
    SubmissionComment,
    SubmissionEvent,
)


class VariantSelectionViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='teacher', password='secret')
        self.source = Source.objects.create(name='Источник')
        self.part = PartOfEGE.objects.create(name='Часть 1')
        self.type_1 = TypeInEGE.objects.create(number=1, max_score=1, part_ege=self.part)
        self.type_2 = TypeInEGE.objects.create(number=2, max_score=1, part_ege=self.part)

        self.problem_1 = Problem.objects.create(
            text='Первая задача',
            complexity=2,
            author=self.user,
            source=self.source,
            type_ege=self.type_1,
        )
        self.problem_2 = Problem.objects.create(
            text='Вторая задача',
            complexity=6,
            author=self.user,
            source=self.source,
            type_ege=self.type_2,
        )
        self.problem_3 = Problem.objects.create(
            text='Третья задача',
            complexity=1,
            author=self.user,
            source=self.source,
            type_ege=self.type_1,
        )

    def test_problem_endpoint_adds_and_removes_problem_in_session(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('variants:current-problem'),
            {'action': 'add', 'problem_id': self.problem_1.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['problem_ids'], [self.problem_1.id])

        response = self.client.post(
            reverse('variants:current-problem'),
            {'action': 'remove', 'problem_id': self.problem_1.id},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['problem_ids'], [])

    def test_generate_variant_creates_persistent_variant_with_owner(self):
        session = self.client.session
        session['current_variant_problem_ids'] = [self.problem_1.id, self.problem_2.id]
        session.save()
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('variants:current'),
            {
                'action': 'generate',
                'show_answers': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        variant = Variant.objects.get()
        self.assertEqual(variant.owner, self.user)
        self.assertEqual(list(variant.problems.values_list('id', flat=True)), [self.problem_1.id, self.problem_2.id])
        self.assertEqual(variant.complexity, 4.0)
        self.assertTrue(variant.show_answers)
        self.assertFalse(variant.is_published)

    def test_repeat_generate_redirects_to_last_variant_without_duplicate(self):
        session = self.client.session
        session['current_variant_problem_ids'] = [self.problem_1.id, self.problem_2.id]
        session.save()
        self.client.force_login(self.user)

        first_response = self.client.post(
            reverse('variants:current'),
            {
                'action': 'generate',
                'show_source': 'on',
            },
        )
        self.assertEqual(first_response.status_code, 302)
        first_variant = Variant.objects.get()

        second_response = self.client.post(
            reverse('variants:current'),
            {
                'action': 'generate',
                'show_source': 'on',
            },
        )
        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(Variant.objects.count(), 1)
        self.assertEqual(second_response.url, f'{first_variant.get_absolute_url()}?answers_created=1')

    def test_full_variant_checkbox_allows_custom_structure(self):
        session = self.client.session
        session['current_variant_problem_ids'] = [self.problem_1.id, self.problem_2.id]
        session.save()
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('variants:current'),
            {
                'action': 'generate',
                'is_full': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        variant = Variant.objects.get()
        self.assertTrue(variant.is_full)
        self.assertFalse(variant.sort_by_complexity)

    def test_sort_by_type_orders_by_type_then_complexity(self):
        session = self.client.session
        session['current_variant_problem_ids'] = [self.problem_2.id, self.problem_1.id, self.problem_3.id]
        session.save()
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('variants:current'),
            {
                'action': 'generate',
                'sort_by_type': 'on',
                'sort_by_complexity': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        variant = Variant.objects.get()
        self.assertTrue(variant.sort_by_type)
        self.assertFalse(variant.sort_by_complexity)
        self.assertEqual([problem.id for problem in variant.get_problems()], [self.problem_3.id, self.problem_1.id, self.problem_2.id])

    def test_answers_link_is_not_exposed_to_anonymous_user_by_query_param(self):
        variant = Variant.objects.create(owner=self.user, answer_slug='abcd')
        variant.problems.set([self.problem_1.id])

        response = self.client.get(f'{variant.get_absolute_url()}?answers_created=1')

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, variant.get_answers_url())


class HomeworkAssignmentFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username='owner', password='secret')
        self.teacher = User.objects.create_user(username='teacher2', password='secret')
        self.teacher.profile.approve_teacher()
        self.teacher.profile.save()
        self.student = User.objects.create_user(username='student1', password='secret')
        self.other_student = User.objects.create_user(username='student2', password='secret')
        self.admin = User.objects.create_superuser(
            username='admin',
            password='secret',
            email='admin@example.com',
        )

        TeacherStudentLink.objects.create(
            teacher=self.teacher,
            student=self.student,
            created_by=self.admin,
        )

        self.source = Source.objects.create(name='Источник')
        self.part = PartOfEGE.objects.create(name='Часть 1')
        self.type_1 = TypeInEGE.objects.create(number=1, max_score=2, part_ege=self.part)
        self.problem = Problem.objects.create(
            text='Задача для ДЗ',
            complexity=4,
            author=self.owner,
            source=self.source,
            type_ege=self.type_1,
        )
        self.variant = Variant.objects.create(owner=self.owner, text='Готовый вариант')
        self.variant.problems.set([self.problem])

    def test_approved_teacher_can_assign_existing_variant(self):
        self.client.force_login(self.teacher)

        response = self.client.post(
            reverse('homework:create', kwargs={'variant_id': self.variant.id}),
            {
                'title': 'Домашка 1',
                'instructions': 'Решить к пятнице',
                'allow_late_submissions': 'on',
                'max_score_strategy': HomeworkAssignment.MaxScoreStrategy.AUTO,
                'target_students': [self.student.id],
            },
        )

        self.assertEqual(response.status_code, 302)
        assignment = HomeworkAssignment.objects.get()
        self.assertEqual(assignment.variant, self.variant)
        self.assertEqual(assignment.created_by, self.teacher)
        self.assertEqual(list(assignment.target_students.values_list('id', flat=True)), [self.student.id])
        submission = HomeworkSubmission.objects.get(assignment=assignment, student=self.student)
        self.assertEqual(submission.max_score_snapshot, self.type_1.max_score)

    def test_teacher_cannot_assign_variant_to_unrelated_student(self):
        self.client.force_login(self.teacher)

        response = self.client.post(
            reverse('homework:create', kwargs={'variant_id': self.variant.id}),
            {
                'title': 'Домашка 2',
                'max_score_strategy': HomeworkAssignment.MaxScoreStrategy.AUTO,
                'target_students': [self.other_student.id],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Нужно выбрать хотя бы одного ученика или одну группу.')
        self.assertEqual(HomeworkAssignment.objects.count(), 0)

    def test_unapproved_teacher_cannot_open_assignment_form(self):
        pending_teacher = User.objects.create_user(username='pending', password='secret')
        pending_teacher.profile.role = pending_teacher.profile.Role.TEACHER
        pending_teacher.profile.teacher_approval_status = pending_teacher.profile.TeacherApprovalStatus.PENDING
        pending_teacher.profile.save()
        self.client.force_login(pending_teacher)

        response = self.client.get(
            reverse('homework:create', kwargs={'variant_id': self.variant.id})
        )

        self.assertEqual(response.status_code, 403)

    def test_admin_can_assign_existing_variant(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('homework:create', kwargs={'variant_id': self.variant.id}),
            {
                'title': 'Админ назначил',
                'max_score_strategy': HomeworkAssignment.MaxScoreStrategy.AUTO,
                'target_students': [self.student.id, self.other_student.id],
            },
        )

        self.assertEqual(response.status_code, 302)
        assignment = HomeworkAssignment.objects.get(title='Админ назначил')
        self.assertEqual(assignment.created_by, self.admin)
        self.assertEqual(assignment.submissions.count(), 2)


class HomeworkStudentSubmissionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(username='owner2', password='secret')
        self.teacher = User.objects.create_user(username='teacher3', password='secret')
        self.teacher.profile.approve_teacher()
        self.teacher.profile.save()
        self.student = User.objects.create_user(username='student3', password='secret')
        TeacherStudentLink.objects.create(
            teacher=self.teacher,
            student=self.student,
            created_by=self.teacher,
        )

        self.source = Source.objects.create(name='Источник 2')
        self.part = PartOfEGE.objects.create(name='Часть 1')
        self.part_2 = PartOfEGE.objects.create(name='Часть 2')
        self.type_1 = TypeInEGE.objects.create(number=1, max_score=1, part_ege=self.part)
        self.type_20 = TypeInEGE.objects.create(number=20, max_score=1, part_ege=self.part)
        self.type_18 = TypeInEGE.objects.create(number=18, max_score=2, part_ege=self.part)
        self.type_10 = TypeInEGE.objects.create(number=10, max_score=2, part_ege=self.part)
        self.type_21 = TypeInEGE.objects.create(number=21, max_score=2, part_ege=self.part_2)
        self.problem_1 = Problem.objects.create(
            text='Задача 1',
            answer='3,5',
            complexity=2,
            author=self.owner,
            source=self.source,
            type_ege=self.type_1,
        )
        self.problem_2 = Problem.objects.create(
            text='Задача 20',
            answer='21',
            complexity=3,
            author=self.owner,
            source=self.source,
            type_ege=self.type_20,
        )
        self.problem_3 = Problem.objects.create(
            text='Задача 18',
            answer='234',
            complexity=5,
            author=self.owner,
            source=self.source,
            type_ege=self.type_18,
        )
        self.problem_4 = Problem.objects.create(
            text='Задача 10',
            answer='24',
            complexity=4,
            author=self.owner,
            source=self.source,
            type_ege=self.type_10,
        )
        self.problem_5 = Problem.objects.create(
            text='Задача 21',
            complexity=5,
            author=self.owner,
            source=self.source,
            type_ege=self.type_21,
        )
        self.variant = Variant.objects.create(owner=self.owner, text='Вариант для сдачи', is_full=True)
        self.variant.problems.set([self.problem_1, self.problem_2, self.problem_3, self.problem_4])
        self.assignment = HomeworkAssignment.objects.create(
            variant=self.variant,
            created_by=self.teacher,
            title='Домашка для ученика',
            max_score_strategy=HomeworkAssignment.MaxScoreStrategy.AUTO,
        )
        self.assignment.target_students.set([self.student])
        self.assignment.ensure_submissions()
        self.submission = HomeworkSubmission.objects.get(assignment=self.assignment, student=self.student)

    def test_student_can_open_assignment_detail(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse('homework:detail', kwargs={'pk': self.assignment.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Моя работа')
        self.assertContains(response, 'Сдать работу')

    def test_student_can_save_draft_answers(self):
        self.client.force_login(self.student)

        response = self.client.post(
            reverse('homework:detail', kwargs={'pk': self.assignment.id}),
            {
                'action': 'save_draft',
                'answer_%s' % self.problem_1.id: '3.5',
                'answer_%s' % self.problem_2.id: '12',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, HomeworkSubmission.Status.DRAFT)
        answer = HomeworkSubmissionAnswer.objects.get(submission=self.submission, problem=self.problem_1)
        self.assertEqual(answer.answer_text, '3.5')
        self.assertTrue(
            SubmissionEvent.objects.filter(
                submission=self.submission,
                event_type=SubmissionEvent.EventType.DRAFT_SAVED,
            ).exists()
        )

    def test_student_autosave_updates_answers(self):
        self.client.force_login(self.student)

        response = self.client.post(
            reverse('homework:autosave', kwargs={'pk': self.assignment.id}),
            {
                'answer_%s' % self.problem_3.id: '243',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, HomeworkSubmission.Status.DRAFT)
        answer = HomeworkSubmissionAnswer.objects.get(submission=self.submission, problem=self.problem_3)
        self.assertEqual(answer.answer_text, '243')

    def test_submit_grades_test_part(self):
        self.client.force_login(self.student)

        response = self.client.post(
            reverse('homework:detail', kwargs={'pk': self.assignment.id}),
            {
                'action': 'submit',
                'answer_%s' % self.problem_1.id: '3.5',
                'answer_%s' % self.problem_2.id: '12',
                'answer_%s' % self.problem_3.id: '23',
                'answer_%s' % self.problem_4.id: '21',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, HomeworkSubmission.Status.SUBMITTED)
        self.assertEqual(float(self.submission.auto_score), 4.0)
        self.assertEqual(float(self.submission.total_score), 4.0)
        answer_20 = HomeworkSubmissionAnswer.objects.get(submission=self.submission, problem=self.problem_2)
        self.assertTrue(answer_20.is_correct)
        answer_18 = HomeworkSubmissionAnswer.objects.get(submission=self.submission, problem=self.problem_3)
        self.assertEqual(float(answer_18.score_awarded), 1.0)
        answer_10 = HomeworkSubmissionAnswer.objects.get(submission=self.submission, problem=self.problem_4)
        self.assertEqual(float(answer_10.score_awarded), 1.0)
        self.assertFalse(answer_10.is_correct)

    def test_student_can_upload_attachment_and_comment(self):
        self.client.force_login(self.student)
        file_obj = SimpleUploadedFile('part2.jpg', b'fake-image-content', content_type='image/jpeg')

        upload_response = self.client.post(
            reverse('homework:detail', kwargs={'pk': self.assignment.id}),
            {
                'action': 'upload_attachments',
                'attachments': file_obj,
            },
        )
        comment_response = self.client.post(
            reverse('homework:detail', kwargs={'pk': self.assignment.id}),
            {
                'action': 'add_comment',
                'body': 'Посмотрите, пожалуйста, вторую часть.',
            },
        )

        self.assertEqual(upload_response.status_code, 302)
        self.assertEqual(comment_response.status_code, 302)
        self.assertEqual(SubmissionAttachment.objects.filter(submission=self.submission).count(), 1)
        self.assertTrue(
            SubmissionComment.objects.filter(
                submission=self.submission,
                author=self.student,
                body='Посмотрите, пожалуйста, вторую часть.',
            ).exists()
        )

    def test_teacher_can_comment_and_review_submission(self):
        self.client.force_login(self.student)
        self.client.post(
            reverse('homework:detail', kwargs={'pk': self.assignment.id}),
            {
                'action': 'submit',
                'answer_%s' % self.problem_1.id: '3.5',
            },
        )

        self.client.force_login(self.teacher)
        comment_response = self.client.post(
            reverse('homework:detail', kwargs={'pk': self.assignment.id}),
            {
                'action': 'teacher_comment',
                'submission_id': self.submission.id,
                'body': 'Вторую часть проверю позже.',
            },
        )
        review_response = self.client.post(
            reverse('homework:detail', kwargs={'pk': self.assignment.id}),
            {
                'action': 'mark_reviewed',
                'submission_id': self.submission.id,
                'manual_score': '3',
            },
        )

        self.assertEqual(comment_response.status_code, 302)
        self.assertEqual(review_response.status_code, 302)
        self.submission.refresh_from_db()
        self.assertEqual(self.submission.status, HomeworkSubmission.Status.REVIEWED)
        self.assertEqual(float(self.submission.manual_score), 3.0)
        self.assertTrue(
            SubmissionComment.objects.filter(
                submission=self.submission,
                author=self.teacher,
                body='Вторую часть проверю позже.',
            ).exists()
        )

    def test_submit_without_second_part_content_auto_reviews_with_zero(self):
        variant = Variant.objects.create(owner=self.owner, text='Вариант со второй частью', is_full=True)
        variant.problems.set([self.problem_1, self.problem_5])
        assignment = HomeworkAssignment.objects.create(
            variant=variant,
            created_by=self.teacher,
            title='Автоноль',
            max_score_strategy=HomeworkAssignment.MaxScoreStrategy.AUTO,
            allow_second_part_text=False,
        )
        assignment.target_students.set([self.student])
        assignment.ensure_submissions()
        submission = HomeworkSubmission.objects.get(assignment=assignment, student=self.student)

        self.client.force_login(self.student)
        response = self.client.post(
            reverse('homework:detail', kwargs={'pk': assignment.id}),
            {
                'action': 'submit',
                f'answer_{self.problem_1.id}': '3.5',
            },
        )

        self.assertEqual(response.status_code, 302)
        submission.refresh_from_db()
        self.assertEqual(submission.status, HomeworkSubmission.Status.REVIEWED)
        self.assertEqual(float(submission.auto_score), 1.0)
        self.assertEqual(float(submission.manual_score), 0.0)
        self.assertTrue(
            SubmissionEvent.objects.filter(
                submission=submission,
                event_type=SubmissionEvent.EventType.REVIEWED,
                payload__auto_zero_second_part=True,
            ).exists()
        )

    def test_teacher_can_store_second_part_scores_per_problem(self):
        variant = Variant.objects.create(owner=self.owner, text='Вариант со второй частью', is_full=True)
        variant.problems.set([self.problem_1, self.problem_5])
        assignment = HomeworkAssignment.objects.create(
            variant=variant,
            created_by=self.teacher,
            title='Разбивка второй части',
            max_score_strategy=HomeworkAssignment.MaxScoreStrategy.AUTO,
            second_part_mode=HomeworkAssignment.SecondPartMode.PER_PROBLEM,
        )
        assignment.target_students.set([self.student])
        assignment.ensure_submissions()
        submission = HomeworkSubmission.objects.get(assignment=assignment, student=self.student)
        self.client.force_login(self.student)
        self.client.post(
            reverse('homework:detail', kwargs={'pk': assignment.id}),
            {
                'action': 'upload_problem_attachments',
                'problem_id': self.problem_5.id,
                'attachments': SimpleUploadedFile('part2.jpg', b'fake-image-content', content_type='image/jpeg'),
            },
        )
        self.client.post(
            reverse('homework:detail', kwargs={'pk': assignment.id}),
            {
                'action': 'submit',
                f'answer_{self.problem_1.id}': '3.5',
            },
        )

        self.client.force_login(self.teacher)
        response = self.client.post(
            reverse('homework:detail', kwargs={'pk': assignment.id}),
            {
                'action': 'mark_reviewed',
                'submission_id': submission.id,
                'manual_score': '0',
                f'problem_score_{self.problem_5.id}': '2',
            },
        )

        self.assertEqual(response.status_code, 302)
        submission.refresh_from_db()
        self.assertEqual(submission.status, HomeworkSubmission.Status.REVIEWED)
        self.assertEqual(float(submission.manual_score), 2.0)
        self.assertTrue(
            HomeworkSubmissionSecondPartScore.objects.filter(
                submission=submission,
                problem=self.problem_5,
                score_awarded=2,
            ).exists()
        )

    def test_student_homework_list_hides_variant_number(self):
        self.client.force_login(self.student)

        response = self.client.get(reverse('homework:list'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Вариант:')
