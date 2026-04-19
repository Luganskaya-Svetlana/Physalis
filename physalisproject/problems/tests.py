from django.contrib import admin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.forms import modelform_factory
from django.test import TestCase
from django.test.client import RequestFactory
from django.urls import reverse

from problems.admin import ProblemAdmin
from problems.models import (
    Justification,
    JustificationGroup,
    Law,
    PartOfEGE,
    Problem,
    ProblemSolutionMethod,
    Source,
    TypeInEGE,
)
from problems.views import evaluate_answer


class SimilarProblemsAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(
            username='admin-user',
            password='secret',
            email='admin@example.com',
        )
        self.admin = ProblemAdmin(Problem, admin.site)

    def save_problem_with_similars(self, problem, similar_problems):
        form_class = modelform_factory(Problem, fields=('text', 'similar_problems'))
        form = form_class(
            data={
                'text': problem.text,
                'similar_problems': [item.pk for item in similar_problems],
            },
            instance=problem,
        )
        self.assertTrue(form.is_valid(), form.errors)

        request = self.factory.post('/admin/problems/problem/')
        request.user = self.user

        obj = form.save(commit=False)
        self.admin.save_model(request, obj, form, change=True)
        self.admin.save_related(request, form, [], change=True)

    def test_single_admin_save_syncs_links_for_all_selected_similar_problems(self):
        problem = Problem.objects.create(text='A', author=self.user)
        similar_one = Problem.objects.create(text='B', author=self.user)
        similar_two = Problem.objects.create(text='C', author=self.user)

        self.save_problem_with_similars(problem, [similar_one, similar_two])

        self.assertCountEqual(
            problem.similar_problems.values_list('id', flat=True),
            [similar_one.id, similar_two.id],
        )
        self.assertCountEqual(
            similar_one.similar_problems.values_list('id', flat=True),
            [problem.id, similar_two.id],
        )
        self.assertCountEqual(
            similar_two.similar_problems.values_list('id', flat=True),
            [problem.id, similar_one.id],
        )

    def test_selecting_one_problem_from_group_connects_entire_group(self):
        similar_one = Problem.objects.create(text='A', author=self.user)
        similar_two = Problem.objects.create(text='B', author=self.user)
        problem = Problem.objects.create(text='C', author=self.user)

        self.save_problem_with_similars(similar_one, [similar_two])
        self.save_problem_with_similars(problem, [similar_one])

        self.assertCountEqual(
            problem.similar_problems.values_list('id', flat=True),
            [similar_one.id, similar_two.id],
        )
        self.assertCountEqual(
            similar_one.similar_problems.values_list('id', flat=True),
            [problem.id, similar_two.id],
        )
        self.assertCountEqual(
            similar_two.similar_problems.values_list('id', flat=True),
            [problem.id, similar_one.id],
        )

    def test_clearing_similar_problems_detaches_problem_and_keeps_old_group(self):
        problem = Problem.objects.create(text='A', author=self.user)
        similar_one = Problem.objects.create(text='B', author=self.user)
        similar_two = Problem.objects.create(text='C', author=self.user)

        self.save_problem_with_similars(problem, [similar_one, similar_two])
        self.save_problem_with_similars(problem, [])

        self.assertCountEqual(
            problem.similar_problems.values_list('id', flat=True),
            [],
        )
        self.assertCountEqual(
            similar_one.similar_problems.values_list('id', flat=True),
            [similar_two.id],
        )
        self.assertCountEqual(
            similar_two.similar_problems.values_list('id', flat=True),
            [similar_one.id],
        )


class ProblemNavigationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='navigation-user',
            password='secret',
        )

    def test_detail_navigation_uses_nearest_existing_problem_ids(self):
        Problem.objects.create(
            id=1681,
            text='Предыдущая задача',
            author=self.user,
        )
        Problem.objects.create(
            id=1683,
            text='Текущая задача',
            author=self.user,
        )

        response = self.client.get(reverse('problems:detail', kwargs={'pk': 1683}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['previous_problem_id'], 1681)
        self.assertIsNone(response.context['next_problem_id'])
        self.assertContains(response, 'href="/problems/1681/"')
        self.assertNotContains(response, 'href="/problems/1682/"')


class EvaluateAnswerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='trainer-user',
            password='secret',
        )
        self.problem = Problem.objects.create(
            text='Тестовая задача',
            author=self.user,
        )

    def create_method(self, title, laws, justifications):
        method = ProblemSolutionMethod.objects.create(
            problem=self.problem,
            title=title,
            is_active=True,
        )
        method.laws.set(laws)
        method.optional_laws.set([])
        method.justifications.set(justifications)
        return method

    def create_method_with_optional_laws(
        self,
        title,
        laws,
        optional_laws,
        justifications,
    ):
        method = ProblemSolutionMethod.objects.create(
            problem=self.problem,
            title=title,
            is_active=True,
        )
        method.laws.set(laws)
        method.optional_laws.set(optional_laws)
        method.justifications.set(justifications)
        return method

    def test_exact_law_match_wins_over_better_justification_match(self):
        law_a = Law.objects.create(name='a')
        law_b = Law.objects.create(name='b')
        law_c = Law.objects.create(name='c')

        justifications = [
            Justification.objects.create(text=str(index))
            for index in range(1, 6)
        ]

        method_one = self.create_method(
            'method-one',
            [law_a, law_b],
            justifications[:4],
        )
        method_two = self.create_method(
            'method-two',
            [law_a, law_b, law_c],
            justifications,
        )

        evaluation = evaluate_answer(
            [method_one, method_two],
            selected_law_ids={law_a.id, law_b.id, law_c.id},
            selected_justification_ids={item.id for item in justifications[:4]},
        )

        self.assertEqual(evaluation['best']['method'].id, method_two.id)
        self.assertEqual(evaluation['best']['extra_laws'], set())
        self.assertEqual(
            evaluation['best']['missing_justifications'],
            {justifications[4].id},
        )

    def test_fewer_law_errors_win_when_no_exact_law_match_exists(self):
        law_a = Law.objects.create(name='law-a')
        law_b = Law.objects.create(name='law-b')
        law_c = Law.objects.create(name='law-c')
        law_d = Law.objects.create(name='law-d')

        justification = Justification.objects.create(text='основание')

        method_one = self.create_method(
            'method-one',
            [law_a, law_b],
            [justification],
        )
        method_two = self.create_method(
            'method-two',
            [law_a, law_b, law_c, law_d],
            [justification],
        )

        evaluation = evaluate_answer(
            [method_one, method_two],
            selected_law_ids={law_a.id, law_b.id, law_c.id},
            selected_justification_ids={justification.id},
        )

        self.assertEqual(evaluation['best']['method'].id, method_one.id)
        self.assertEqual(evaluation['best']['extra_laws'], {law_c.id})

    def test_group_shows_soft_message_when_more_than_minimum_is_selected(self):
        law_a = Law.objects.create(name='law-group')
        justifications = [
            Justification.objects.create(text=f'group-{index}')
            for index in range(1, 4)
        ]

        method = self.create_method(
            'method-with-group',
            [law_a],
            [],
        )
        group = JustificationGroup.objects.create(
            method=method,
            title='Проверочная группа',
            min_selected=1,
            max_selected=len(justifications),
        )
        group.justifications.set(justifications)

        evaluation = evaluate_answer(
            [method],
            selected_law_ids={law_a.id},
            selected_justification_ids={item.id for item in justifications[:2]},
        )

        self.assertEqual(
            evaluation['soft_messages'],
            [{
                'selected_items': ['group-1', 'group-2'],
                'suffix': 'достаточно выбрать один любой пункт.',
            }],
        )

    def test_optional_law_is_not_marked_as_extra(self):
        law_a = Law.objects.create(name='required-law')
        law_b = Law.objects.create(name='optional-law')
        justification = Justification.objects.create(text='основание optional')

        method = self.create_method_with_optional_laws(
            'method-with-optional-law',
            [law_a],
            [law_b],
            [justification],
        )

        evaluation = evaluate_answer(
            [method],
            selected_law_ids={law_a.id, law_b.id},
            selected_justification_ids={justification.id},
        )

        self.assertTrue(evaluation['passed'])
        self.assertEqual(evaluation['best']['extra_laws'], set())
        self.assertEqual(evaluation['best']['missing_laws'], set())


class ReferenceDataValidationTests(TestCase):
    def test_part_alias_is_normalized_to_canonical_name(self):
        part = PartOfEGE.objects.create(name='Часть 1')
        self.assertEqual(part.name, 'Первая часть')

    def test_unknown_part_name_is_rejected(self):
        with self.assertRaises(ValidationError):
            PartOfEGE.objects.create(name='Р')

    def test_source_name_must_not_be_single_character(self):
        source = Source(name='S')
        with self.assertRaises(ValidationError):
            source.full_clean()

    def test_type_number_is_unique_within_part(self):
        part = PartOfEGE.objects.create(name='Первая часть')
        TypeInEGE.objects.create(number=1, max_score=1, part_ege=part)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                TypeInEGE.objects.create(number=1, max_score=2, part_ege=part)
