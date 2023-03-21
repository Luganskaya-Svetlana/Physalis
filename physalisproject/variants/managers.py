from django.db import models


class VariantManager(models.Manager):
    def list(self):
        return (
            self.get_queryset()
                .only('id', 'complexity', 'text')
        )

    def detail(self):
        return (
            self.get_queryset()
                .prefetch_related('problems')
                .only('id', 'complexity', 'text', 'problem__text',
                      'problem__type_ege__number')
        )

    def answers(self):
        return (
            self.get_queryset()
                .prefetch_related('problems')
                .only('id', 'problem__solution', 'problem__answer',
                      'problem__type_ege__number')
        )
