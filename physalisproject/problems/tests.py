from django.contrib.auth.models import User
from django.test import TestCase

from problems.models import Justification, Law, Problem, ProblemSolutionMethod
from problems.views import evaluate_answer


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
