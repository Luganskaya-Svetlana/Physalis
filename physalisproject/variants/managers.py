from django.db import models


class VariantManager(models.Manager):
    def list(self):
        return (
            self.get_queryset()
                .only('id', 'complexity', 'text', 'is_full')
                .filter(is_published=True)
        )

    def detail(self):
        return (
            self.get_queryset()
                .only(
                    'id',
                    'complexity',
                    'text',
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
                    'owner_id',
                )
        )

    def answers(self):
        return (
            self.get_queryset()
                .only('id', 'is_full', 'sort_by_complexity', 'sort_by_type')
        )
