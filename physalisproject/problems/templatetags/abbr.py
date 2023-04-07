from django import template
from django.template.defaultfilters import stringfilter


def replace_by_dic(el, dic):
    for i, j in dic.items():
        el = el.replace(i, j)
    return el


abbr_dic = {
    'ans': 'Ответ: <span class=ans>                           </span>',
    'anpm': 'Ответ: (<span class=ans>              </span>\
             ± <span class=ans>              </span>)',
    'table_ab': 'Ответ:<table class="change"><tr><td>А</td><td>Б</td></tr>\
                 <tr><td>&nbsp;</td><td></td></tr></table>',
    'table_av': 'Ответ:<table class="change"><tr><td>А</td><td>Б</td>\
                 <td>В</td></tr><tr><td>&nbsp;</td><td></td><td></td></tr>\
                 </table>'
}


register = template.Library()


@register.filter()
@stringfilter
def abbr(value):
    return replace_by_dic(value, abbr_dic)
