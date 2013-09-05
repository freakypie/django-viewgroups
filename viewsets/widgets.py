from django import forms
from django.utils.encoding import force_unicode


class AutocompleteWidget(forms.TextInput):

    def render(self, name, value, attrs=None):
        if value:
            attrs.update({
                "data-text": force_unicode(value),
            })
            value = value.pk
        return forms.TextInput.render(self, name, value, attrs=attrs)
