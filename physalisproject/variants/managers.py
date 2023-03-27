from django.db import models


class VariantManager(models.Manager):
    def list(self):
        return (
            self.get_queryset()
                .only('id', 'complexity', 'text', 'is_full')
        )

    def detail(self):
        return (
            self.get_queryset()
                .prefetch_related('problems')
                .only('id', 'complexity', 'text', 'problems__text',
                      'problems__type_ege__number')
        )

    def answers(self):
        return (
            self.get_queryset()
                .prefetch_related('problems')
                .only('id', 'problems__solution', 'problems__answer',
                      'problems__type_ege__number')
        )
