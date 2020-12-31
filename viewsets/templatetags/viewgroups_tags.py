from crispy_forms.bootstrap import StrictButton
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Fieldset
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


@register.filter
def message_type_bootstraped(message_type):
    if message_type == "error":
        return "danger"
    return message_type


@register.simple_tag()
def form_helper(
        button=None,
        form=None,
        formset=None,
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

    if formset:
        helper.template = "bootstrap/table_inline_formset.html"

    if form and button:
        helper.layout.fields.append(
            Div(
                Div(
                    StrictButton(button, css_class="btn btn-default", type="submit"),
                    css_class="col-md-{} col-md-offset-{}".format(
                        field_size, (label_size + label_offset)
                    )
                ),
                css_class="form-group"
            )
        )
    return helper
