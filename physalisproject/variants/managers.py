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
                .only('id', 'complexity', 'text', 'show_answers')
        )

    def answers(self):
        return (
            self.get_queryset()
                .only('id')
        )
