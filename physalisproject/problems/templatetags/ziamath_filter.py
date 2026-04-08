from pathlib import Path
import re
import xml.etree.ElementTree as ET

import ziamath as zm
from django import template

ET.register_namespace("", "http://www.w3.org/2000/svg")

FONT_PATH = Path(__file__).resolve().parents[2] / 'fonts' / 'STIXTwoMath5.otf'

zm.config.math.mathfont = str(FONT_PATH)
# STIX 2.13b171 with ℰ symbol copied from stix-1.0.0 with fontforge
# zm.config.precision = 2
# zm.config.minsizefraction = .6

zm.config.svg2 = False
zm.config.decimal_separator = ','
# zm.config.math.variant = 'sans'


register = template.Library()

shortcuts = {
    r'\\uppi(?![a-zA-Z])': r'\\mathrm{\\pi}',
    r'\\a(?![a-zA-Z])': r'\\alpha',
    r'\\b(?![a-zA-Z])': r'\\beta',
    r'\\f(?![a-zA-Z])': r'\\varphi',
    r'\\e(?![a-zA-Z])': r'\\varepsilon',
    r'\\la(?![a-zA-Z])': r'\\lambda',
    r'\\cmc(?![a-zA-Z])': r'\\;см^3',
    r'\\mc(?![a-zA-Z])': r'\\;м^3',
    r'\\kg(?![a-zA-Z])': r'\\;кг',
    r'\\kgms(?![a-zA-Z])': r'\\;кг\\cdot м/с',
    r'\\kgmc(?![a-zA-Z])': r'\\;кг/м^3',
    r'\\gmc(?![a-zA-Z])': r'\\;г/м^3',
    r'\\gcmc(?![a-zA-Z])': r'\\;г/см^3',
    r'\\s(?![a-zA-Z])': r'\\;с',
    r'\\m(?![a-zA-Z])': r'\\;м',
    r'\\km(?![a-zA-Z])': r'\\;км',
    r'\\A(?![a-zA-Z])': r'\\;А',
    r'\\Am(?![a-zA-Z])': r'\\;А',
    r'\\mA(?![a-zA-Z])': r'\\;мА',
    r'\\Om(?![a-zA-Z])': r'\\;Ом',
    r'\\g(?![a-zA-Z])': r'\\;г',
    r'\\Hz(?![a-zA-Z])': r'\\;Гц',
    r'\\eV(?![a-zA-Z])': r'\\;эВ',
    r'\\Wt(?![a-zA-Z])': r'\\;Вт',
    r'\\kWt(?![a-zA-Z])': r'\\;кВт',
    r'\\mol(?![a-zA-Z])': r'\\;моль',
    r'\\gmol(?![a-zA-Z])': r'\\;г/моль',
    r'\\kgmol(?![a-zA-Z])': r'\\;кг/моль',
    r'\\JmolK(?![a-zA-Z])': r'\\;Дж/(моль\\cdot К)',
    r'\\cm(?![a-zA-Z])': r'\\;см',
    r'\\mm(?![a-zA-Z])': r'\\;мм',
    r'\\nm(?![a-zA-Z])': r'\\;нм',
    r'\\Vo(?![a-zA-Z])': r'\\;В',
    r'\\K(?![a-zA-Z])': r'\\;К',
    r'\\Vm(?![a-zA-Z])': r'\\;В/м',
    r'\\Pa(?![a-zA-Z])': r'\\;Па',
    r'\\kPa(?![a-zA-Z])': r'\\;кПа',
    r'\\mmrt(?![a-zA-Z])': r'\\;мм\\hspace{1.7mm}рт.\\hspace{1.6mm}ст.',
    r'\\ms(?![a-zA-Z])': r'\\;м/с',
    r'\\kmh(?![a-zA-Z])': r'\\;км/ч',
    r'\\mss(?![a-zA-Z])': r'\\;м/с^2',
    r'\\cms(?![a-zA-Z])': r'\\;см/с',
    r'\\mmsq(?![a-zA-Z])': r'\\;мм^2',
    r'\\cmsq(?![a-zA-Z])': r'\\;см^2',
    r'\\msq(?![a-zA-Z])': r'\\;м^2',
    r'\\Cl(?![a-zA-Z])': r'\\;Кл',
    r'\\Tl(?![a-zA-Z])': r'\\;Тл',
    r'\\Ftr(?![a-zA-Z])': r'F_{тр}',
    r'\\N(?![a-zA-Z])': r'\\;Н',
    r'\\mkF(?![a-zA-Z])': r'\\;мкФ',
    r'\\Gn(?![a-zA-Z])': r'\\;Гн',
    r'\\Nm(?![a-zA-Z])': r'\\;Н/м',
    r'\\J(?![a-zA-Z])': r'\\;Дж',
    r'\\kJ(?![a-zA-Z])': r'\\;кДж',
    r'\\eds(?![a-zA-Z])': r'\\mathscr{E}',
    r'\\const(?![a-zA-Z])': r'\\text{const}',
    r'\\deg(?![a-zA-Z])': r'^\\circ',
    r'\\degc(?![a-zA-Z])': r'~^\\circ\\text{C}',
    r'\\dU(?![a-zA-Z])': r'\\Delta U',
    r'\\dt(?![a-zA-Z])': r'\\Delta t',
    r'\\dx(?![a-zA-Z])': r'\\Delta x',
    r'\\ell(?![a-zA-Z])': r'𝓁',  # 0001D4C1
    # r'\\ell(?![a-zA-Z])': r'𝓵',  # 0001D4F5 (looks bold)
    r'\\dl(?![a-zA-Z])': r'\\Delta 𝓁',
}


def replace_shortcuts(formula):
    try:
        # Шаблон для научной нотации, позволяющий опускать число перед e:
        # \num{e-5} или \num{2.5e3} и т.д.
        scientific_notation_pattern = r'\\num\{([0-9.,]*)[eE]([+-]?\d+)\}'

        def replace_scientific_notation(match):
            number = match.group(1)
            exponent = match.group(2)

            # Если перед e не было числа (пример: \num{e-5}), результатом будет
            # просто 10^{exponent}
            if not number:
                return f'10^{{{exponent}}}'

            # Если число было, заменяем точку на запятую и добавляем умножение
            number = number.replace('.', ',')
            return f'{number} \\cdot 10^{{{exponent}}}'

        formula = re.sub(scientific_notation_pattern,
                         replace_scientific_notation, formula)

        # Предполагается, что словарь shortcuts определен выше
        for shortcut, full_name in shortcuts.items():
            formula = re.sub(shortcut, full_name, formula)

        return formula

    except Exception as e:
        # При необходимости можно логировать или обрабатывать исключение
        raise e


def render_formula(match, display_style=False):
    try:
        formula = match.group(1)
        formula = replace_shortcuts(formula)
        math_obj = zm.Math.fromlatex(formula, size=19)
        svg = math_obj.svg()
        root = ET.fromstring(svg)

        # Set y_offset to align svg with text
        dy = -0.96
        y_offset = math_obj.getyofst() + dy

        # Add style for vertical alignment
        style = root.attrib.get('style', '')
        root.attrib['style'] = f'{style}; vertical-align: {y_offset}px;'

        # Add display style for $$...$$ and don't for $...$
        if display_style:
            svg_class = 'math-svg display'
        else:
            svg_class = 'math-svg'

        svg = ET.tostring(root, encoding='unicode')\
            .replace('<svg', f'<svg class="{svg_class}"')

        # return svg + f'<span class="hidden" data-content="{formula}"></span>'
        # version = importlib.metadata.version('ziamath')
        return svg

    except Exception as e:
        return f'<span style="color: red;">Error formula: {str(e)}</span>'


@register.filter()
def ziamath_filter(text):
    try:
        text = re.sub(
            r'\$\$([^$]*?)\$\$',
            lambda match: render_formula(match, display_style=True),
            text, flags=re.DOTALL
        )
        text = re.sub(r'\$([^$]*?)\$', render_formula, text)
        return text

    except Exception as e:
        return f'<span style="color: red;">Error zm_filter: {str(e)}</span>'
