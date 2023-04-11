from django import template
import ziamath as zm
import re
import xml.etree.ElementTree as ET



register = template.Library()

def replace_shortcuts(formula):
    shortcuts = {
        r'\\a(?![a-zA-Z])': r'\\alpha',
        r'\\b(?![a-zA-Z])': r'\\beta',
        r'\\f(?![a-zA-Z])': r'\\varphi',
        r'\\eds(?![a-zA-Z])': r'\\mathcal{E}',
        r'\\degc(?![a-zA-Z])': r'\\,{}^{\\circ}\\text{C}',
    }

    for shortcut, full_name in shortcuts.items():
        formula = re.sub(shortcut, full_name, formula)

    return formula

def render_formula(match):
    formula = match.group(1)
    formula = replace_shortcuts(formula)  # Заменяем сокращения на полные имена
    #svg = ziamath.to_svg(formula)
    svg = zm.Math.fromlatex(formula, size=20).svg()

    ET.register_namespace('', '')

    root = ET.fromstring(svg)
    style = root.attrib.get('style', '')
    root.attrib['style'] = f'{style}; vertical-align: middle; fontsize:80%; max-height:100%;'
    # Ограничиваем высоту SVG
    height = float(root.attrib.get('height', '0'))
    max_height = 200  # Задаем максимальную высоту (можете выбрать другое значение)
    if height > max_height:
        root.attrib['height'] = str(max_height)
        root.attrib['preserveAspectRatio'] = 'xMinYMin meet'

    svg = ET.tostring(root, encoding='unicode')
    svg = svg.replace('ns0:', '')

    return svg

@register.filter()
def ziamath_filter(text):
    text = re.sub(r'\$\$([^$]*?)\$\$', render_formula, text, flags=re.DOTALL)
    text = re.sub(r'\$([^$]*?)\$', render_formula, text)
    return text
