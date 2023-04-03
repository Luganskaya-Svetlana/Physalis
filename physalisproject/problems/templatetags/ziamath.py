from django import template
from django.template.defaultfilters import stringfilter

import ziamath as zm
import re


register = template.Library()


@register.filter()
@stringfilter

def ziamath(string):
    groups = re.split(r'(\${1,2}[^${]+\$*)', string, flags=re.DOTALL)
    for i in range(len(groups)):
        if groups[i].startswith('$') and groups[i].endswith('$'):
            # Убираем доллары и применяем функцию из ziamath
            groups[i] = zm.Math.fromlatex(groups[i].strip('$')).svg()
    return ''.join(groups)



#def ziamath(value):
    #return zm.zmath.Math.fromlatextext(value).svg()

#def zi(match):
    #group = match.group(1)
    #return zm.Math.fromlatex(group).svg()

#def ziamath(value):
    #return re.sub('\$(.*?)\$', zi, value, flags=re.M)


## Работает с одиночными долларами
#def ziamath(string):
    #groups = string.split('$')
    #for i in range(1, len(groups), 2):
        #groups[i] = zm.Math.fromlatex(groups[i]).svg()
    #result = ''.join(groups)
    #return result

