from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from problems.models import PartOfEGE, Problem, Source, TypeInEGE
from variants.models import Variant


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

    def test_full_variant_checkbox_is_rejected_for_invalid_structure(self):
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

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Полный вариант должен иметь структуру 20+6')
        self.assertEqual(Variant.objects.count(), 0)

    def test_answers_link_is_not_exposed_to_anonymous_user_by_query_param(self):
        variant = Variant.objects.create(owner=self.user, answer_slug='abcd')
        variant.problems.set([self.problem_1.id])

        response = self.client.get(f'{variant.get_absolute_url()}?answers_created=1')

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, variant.get_answers_url())
