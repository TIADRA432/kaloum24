from django import template

from .. import i18n

register = template.Library()


@register.simple_tag(takes_context=True)
def t(context, cle):
    return i18n.traduire(cle, context.get("langue_ui", "fr"))


@register.simple_tag
def couverture():
    return i18n.couverture()
