from crispy_forms.bootstrap import StrictButton
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div
from django.template import Library
from django.contrib.admin.helpers import AdminForm
from django.forms.widgets import Input, CheckboxInput, Select, TextInput, \
    Textarea, CheckboxSelectMultiple

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


@register.simple_tag()
def form_helper(
        button=None,
        form=None,
        form_tag=False,
        label_size=4,
        label_offset=0,
        field_size=8):

    helper = FormHelper()
    helper.form_tag = form_tag

    if label_size:
        helper.label_class = "col-md-{}".format(label_size)
        helper.field_class = "col-md-{}".format(field_size)

    if label_offset:
        helper.label_size = ' col-md-offset-{}'.format(label_offset)

    if form:
        helper.add_layout(helper.build_default_layout(form))

    if form and button:
        helper.layout.fields.append(
            Div(
                Div(
                    StrictButton(button, type="submit"),
                    css_class="col-md-{} col-md-offset-{}".format(
                        field_size, (label_size + label_offset)
                    )
                ),
                css_class="form-group"
            )
        )
    return helper
