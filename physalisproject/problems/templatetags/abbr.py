from django import template
from django.template.defaultfilters import stringfilter
import re


def replace_by_dic(el, dic):
    for i, j in dic.items():
        el = el.replace(i, j)
    return el


def table_change_replace(match):
    string_1 = match.group(1)
    string_2 = match.group(2)
    return f"""Для каждой величины определите соответствующий характер
изменения:

1. увеличивается
2. уменьшается
3. не изменяется

Запишите в таблицу выбранные цифры для каждой физической величины.
Цифры в ответе могут повторяться.


<table class="change center-table">
<tr>
<td> {string_1} </td>
<td> {string_2} </td>
</tr>
<tr>
<td>&nbsp;</td>
<td></td>
</tr>
</table>"""


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
    value = replace_by_dic(value, abbr_dic)
    value = re.sub(r'table_change\[(.+?)\]\[(.+?)\]', table_change_replace,
                   value)
    return value
