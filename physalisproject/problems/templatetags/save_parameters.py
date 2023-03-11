from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def param_save(context, **kwargs):
    """
    Возвращает параметры ссылки,
    сохраняя предыдущие непустые значения и добавляя новые
    """
    answ = context['request'].GET.copy()
    for param, value in kwargs.items():
        answ[param] = value
    for param in [param for param, value in answ.items() if not value]:
        del answ[param]
    return answ.urlencode()
