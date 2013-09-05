from django import forms
from django.utils.encoding import force_unicode
from django.forms.util import flatatt
from django.utils.safestring import mark_safe
from viewsets.widgets import AutocompleteWidget


class AutocompleteField(forms.ModelChoiceField):
    widget = AutocompleteWidget

    def prepare_value(self, value):
        if hasattr(value, '_meta'):
            return value
        if value:
            return self.queryset.get(pk=value)
