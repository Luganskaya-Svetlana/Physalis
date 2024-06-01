from django import template
from django.template.defaultfilters import stringfilter
import markdown as md
# from markdown.extensions.toc import slugify_unicode


register = template.Library()


@register.filter()
@stringfilter
def markdown(value):
    return md.markdown(
        value,
        extensions=[
            'markdown.extensions.fenced_code',
            'markdown.extensions.tables',
            'markdown.extensions.toc',
            'markdown.extensions.footnotes'
        ],
        extension_configs={
            'markdown.extensions.toc': {
                'toc_depth': '2-6',
                # 'slugify': slugify_unicode,
            },
        }
    )
