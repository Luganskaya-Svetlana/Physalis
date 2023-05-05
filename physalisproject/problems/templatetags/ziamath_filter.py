import re
import xml.etree.ElementTree as ET
import ziamath as zm
from django import template

# zm.config.precision = 3
zm.config.svg2 = False

register = template.Library()

shortcuts = {
    # r'([^{]*[A-Z])(?=$|[\s\]])': r'\1\\hspace{0.085em}',
    # r'(?<=\w|\})\\sin(?=\^|\\|{)': r'\\,\\sin',
    # r'(?<=\w|\})\\cos(?=\^|\\|{)': r'\\,\\cos',
    # r'([a-zA-Z])\\dfrac': r'\1\\;\\dfrac',
    # r'\\cdot': r'\\;\\cdot\\;',
    # r"'": r"\\prime ",
    # r'\\tg(?![a-zA-Z])': r'\\,\\text{tg}\,',
    # r'\\ctg(?![a-zA-Z])': r'\\,\\text{ctg}\,',
    # r'\\arctg(?![a-zA-Z])': r'\\text{arctg}~',
    r'\\a(?![a-zA-Z])': r'\\alpha',
    r'\\b(?![a-zA-Z])': r'\\beta',
    r'\\f(?![a-zA-Z])': r'\\varphi',
    r'\\la(?![a-zA-Z])': r'\\lambda',
    r'\\mc(?![a-zA-Z])': r'\\;м^3',
    r'\\kg(?![a-zA-Z])': r'\\;кг',
    r'\\kgms(?![a-zA-Z])': r'\\;кг\\cdot м\!/\!с',
    r'\\kgmc(?![a-zA-Z])': r'\\;кг\! /\! м^3',
    r'\\s(?![a-zA-Z])': r'\\;с',
    r'\\m(?![a-zA-Z])': r'\\;м',
    r'\\A(?![a-zA-Z])': r'\\;А',
    r'\\Om(?![a-zA-Z])': r'\\;Ом',
    r'\\g(?![a-zA-Z])': r'\\;г',
    r'\\Hz(?![a-zA-Z])': r'\\;Гц',
    r'\\eV(?![a-zA-Z])': r'\\;эВ',
    r'\\Wt(?![a-zA-Z])': r'\\;Вт',
    r'\\kWt(?![a-zA-Z])': r'\\;кВт',
    r'\\cm(?![a-zA-Z])': r'\\;см',
    r'\\mm(?![a-zA-Z])': r'\\;мм',
    r'\\nm(?![a-zA-Z])': r'\\;нм',
    r'\\Vo(?![a-zA-Z])': r'\\;В',
    r'\\Vm(?![a-zA-Z])': r'\\;В/м',
    r'\\Pa(?![a-zA-Z])': r'\\;Па',
    r'\\kPa(?![a-zA-Z])': r'\\;кПа',
    r'\\ms(?![a-zA-Z])': r'\\;м\!/\!с',
    r'\\mss(?![a-zA-Z])': r'\\;м\!/\!с^2',
    r'\\cms(?![a-zA-Z])': r'\\;см\!/\!с',
    r'\\cmsq(?![a-zA-Z])': r'\\;см^2',
    r'\\msq(?![a-zA-Z])': r'\\;м^2',
    r'\\Cl(?![a-zA-Z])': r'\\;Кл',
    r'\\Tl(?![a-zA-Z])': r'\\;Тл',
    r'\\Ftr(?![a-zA-Z])': r'F_{тр}',
    r'\\N(?![a-zA-Z])': r'\\;Н',
    r'\\mkF(?![a-zA-Z])': r'\\;мкФ',
    r'\\Nm(?![a-zA-Z])': r'\\;Н\!/\!м',
    r'\\J(?![a-zA-Z])': r'\\;Дж',
    r'\\kJ(?![a-zA-Z])': r'\\;кДж',
    r'\\eds(?![a-zA-Z])': r'\\mathcal{E}',
    r'\\deg(?![a-zA-Z])': r'^\\circ',
    r'\\degc(?![a-zA-Z])': r'~^\\circ\\text{C}',
    r'\\dU(?![a-zA-Z])': r'\\Delta U',
    r'\\dt(?![a-zA-Z])': r'\\Delta t',
    r'\\dx(?![a-zA-Z])': r'\\Delta x',
    r'\\dl(?![a-zA-Z])': r'\\Delta \\ell',
}


def replace_shortcuts(formula):
    for shortcut, full_name in shortcuts.items():
        formula = re.sub(shortcut, full_name, formula)

    return formula


def handle_abbreviations(match):
    abbrev = match.group(1)
    number = match.group(2)
    punct = match.group(3)

    if "e" in number:
        base, exponent = number.split("e")
        base = base.replace(".", "{,}").replace(",", "{,}")
        if base == "1" or base=="":
            formula = f"10^{{{exponent}}}"
        else:
            formula = f"{base} \\cdot 10^{{{exponent}}}"
    elif "." in number or "," in number:
        number = number.replace(".", "{,}")
        formula = f"{number}"
    else:
        formula = f"{number}"

    if abbrev == "\\edsV":
        formula = f"\\eds={formula}\\Vo"
    elif abbrev == "\\UV":
        formula = f"U={formula}\\Vo"
    elif abbrev == "\\rOm":
        formula = f"r={formula}\\Om"
    elif abbrev == "\\ROm":
        formula = f"R={formula}\\Om"
    elif abbrev == "\\RzOm":
        formula = f"R_0={formula}\\Om"
    elif abbrev == "\\RoOm":
        formula = f"R_1={formula}\\Om"
    elif abbrev == "\\RdOm":
        formula = f"R_2={formula}\\Om"
    elif abbrev == "\\CmkF":
        formula = f"C={formula}\\mkF"

    return f"${formula}{punct}$"


def render_formula(match, display_style=False):
    formula = match.group(1)
    formula = replace_shortcuts(formula)
    math_obj = zm.Math.fromlatex(formula, size=18.5)
    svg = math_obj.svg()

    # Удаляем атрибут xmlns:ns0 из тега SVG
    root = ET.fromstring(svg)
    if 'xmlns:ns0' in root.attrib:
        del root.attrib['xmlns:ns0']

    # Получаем размеры и смещение формулы
    # width, height = math_obj.getsize()
    y_offset = math_obj.getyofst()-0.75

    # Добавляем атрибут style для вертикального выравнивания
    style = root.attrib.get('style', '')
    root.attrib['style'] = f'{style}; vertical-align: {y_offset}px;'

    # Если display_style == True, добавляем класс 'display' к SVG
    if display_style:
        svg_class = 'math-svg display'
    else:
        svg_class = 'math-svg'

    svg = ET.tostring(root, encoding='unicode').replace('ns0:', '') \
        .replace('<svg', f'<svg class="{svg_class}"')

    return svg


@register.filter()
def ziamath_filter(text):
    text = re.sub(
        r'(\\edsV|\\UV|\\rOm|\\RzOm|\\ROm|\\CmkF|\\RoOm)\[((?:1)?e\d+|[^[\]]+)\]([.,;]?)',
        handle_abbreviations, text
    )
    text = re.sub(
        r'\$\$([^$]*?)\$\$',
        lambda match: render_formula(match, display_style=True),
        text, flags=re.DOTALL
    )
    text = re.sub(r'\$([^$]*?)\$', render_formula, text)
    return text
