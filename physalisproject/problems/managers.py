from django.db import models


class ProblemManager(models.Manager):
    def list(self):
        return (
            self.get_queryset()
                .select_related('type_ege')
                .only('id', 'complexity', 'text', 'type_ege__number',
                      'solution')
        )

    def detail(self):
        return (
            self.get_queryset()
            .prefetch_related('tags')
            .select_related('author', 'source', 'category', 'subcategory',
                            'type_ege')
        )
