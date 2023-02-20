from django import template
from django.template.defaultfilters import stringfilter

import markdown as md


def replace_by_dic(el, dic):
    for i, j in dic.items():
        el = el.replace(i, j)
    return el


abbr = {
    'table_ab': 'Ответ:<tableclass="change"><tr><td>А</td><td>Б</td></tr>\
                 <tr><td>&nbsp;</td><td></td></tr></table>',
    'table_abv': 'Ответ:<tableclass="change"><tr><td>А</td><td>Б</td>\
                  <td>В</td></tr><tr><td>&nbsp;</td><td></td><td></td></tr>\
                  </table>'
}


register = template.Library()


@register.filter()
@stringfilter
def markdown(value):
    return md.markdown(replace_by_dic(value, abbr),
                       extensions=['markdown.extensions.fenced_code'])
