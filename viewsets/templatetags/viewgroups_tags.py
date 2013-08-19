from django import template
from django.conf import settings


register = template.Library()


@register.filter
def pkslug(obj):
    if "slug" in obj.__dict__:
        return obj.slug
    return obj.pk


@register.filter
def default_form_template(form_type):
    # TODO: switch form based on type
    return getattr(settings, "DEFAULT_FORM_TEMPLATE", "forms/bootstrap3.html")
