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
                    'show_answers',
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
                .only('id')
        )
