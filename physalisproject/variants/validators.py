from string import ascii_lowercase as letters

from django.core.exceptions import ValidationError


def validate_answer_slug(answer_slug):
    for el in answer_slug:
        if el not in letters:
            raise ValidationError('slug для ответов должен '
                                  'содержать только латинские '
                                  'буквы в нижнем регистре')
    if len(answer_slug) != 4:
        raise ValidationError('slug для ответов должен '
                              'содержать ровно 4 символа')
