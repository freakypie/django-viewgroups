from django import forms
from .widgets import AutocompleteWidget


class AutocompleteField(forms.ModelChoiceField):
    widget = AutocompleteWidget

    def prepare_value(self, value):
        if hasattr(value, '_meta'):
            return value
        if value:
            return self.queryset.get(pk=value)
