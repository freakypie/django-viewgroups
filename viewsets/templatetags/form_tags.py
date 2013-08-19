from django.template import Library
from django.contrib.admin.helpers import AdminForm
from django.forms.widgets import Input, CheckboxInput, Select, TextInput, \
    Textarea

register = Library()


@register.filter
def is_input(value):
    return isinstance(value, Input)


@register.filter
def is_text(value):
    return isinstance(value, TextInput)


@register.filter
def is_checkbox(value):
    return isinstance(value, CheckboxInput)


@register.filter
def is_checkbox_multiple(value):
    return isinstance(value, CheckboxSelectMultiple)


@register.filter
def is_select(value):
    return isinstance(value, Select)


@register.filter
def field_list(form, fields):
    return [form[f] for f in fields.split(",")]


@register.filter
def split(fields, delimiter=","):
    return fields.split(delimiter)


@register.filter
def is_type(field, usertype):
    return type(field.field).__name__.lower() == usertype.lower()


@register.filter
def fieldsets(form, fieldsets=None):
    if not fieldsets:
        fieldsets = getattr(form, "fieldsets", None)
    if not fieldsets:
        fieldsets = ((None, {"fields": form.fields.keyOrder}),)

    for name, field in form.fields.items():
        if isinstance(field.widget, (Textarea, TextInput)):
            klass = field.widget.attrs.get('class')
            if not klass:
                field.widget.attrs['class'] = "form-control"

    return AdminForm(form, fieldsets, {})


@register.filter
def line_has_errors(line):
    for fieldcont in line:
        a = fieldcont.field.errors
        if len(fieldcont.field.errors) > 0:
            return True
    return False
