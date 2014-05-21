from django.contrib.admin.filters import SimpleListFilter, FieldListFilter
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.util import get_fields_from_path
from django.contrib.admin.views.main import IGNORED_PARAMS
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.http import urlencode
from viewsets.mixins.base import SessionDataMixin


class QuerysetListFilter(SimpleListFilter):

    def get_choices_queryset(self):
        raise NotImplementedError

    def get_choice_label(self, obj):
        return unicode(obj)

    def lookups(self, request, model_admin):
        for obj in self.get_choices_queryset(request, model_admin):
            yield (obj.pk, self.get_choice_label(obj))

    def queryset(self, request, queryset):
        try:
            return queryset.filter(**self.used_parameters)
        except ValidationError as e:
            raise IncorrectLookupParameters(e)


class FakeRequest(object):

    def __init__(self, request, **kwargs):
        self.original_request = request
        self.user = request.user
        self.GET = request.GET
        self.REQUEST = request.REQUEST
        self.POST = request.POST
        self.META = request.META
        for n, v in kwargs.items():
            setattr(self, n, v)


class FilterMixin(SessionDataMixin):
    """ provides filtering for a queryset """
    list_filter = []
    original_queryset = None

    def get_list_filters(self):
        return self.list_filter

    def get_filter_classes(self):
        lookup_params = self.get_data()

        # Remove all the parameters that are globally and systematically
        # ignored.
        for ignored in IGNORED_PARAMS:
            if ignored in lookup_params:
                del lookup_params[ignored]

        # Normalize the types of keys
        for key, value in lookup_params.items():
            if not isinstance(key, str):
                # 'key' will be used as a keyword argument later, so Python
                # requires it to be a string.
                del lookup_params[key]
                lookup_params["{}".format(key)] = value

        request = FakeRequest(self.request, GET=self.get_data())

        filter_specs = []
        list_filters = self.get_list_filters()
        if list_filters:
            for list_filter in list_filters:
                if callable(list_filter):
                    # This is simply a custom list filter class.
                    spec = list_filter(self.request, lookup_params,
                        self.model, self)
                else:
                    field_path = None
                    if isinstance(list_filter, (tuple, list)):
                        # This is a custom FieldListFilter class for a given field.
                        field, field_list_filter_class = list_filter
                    else:
                        # This is simply a field name, so use the default
                        # FieldListFilter class that has been registered for
                        # the type of the given field.
                        field, field_list_filter_class = list_filter, FieldListFilter.create
                    if not isinstance(field, models.Field):
                        field_path = field
                        field = get_fields_from_path(self.model, field_path)[-1]
                    spec = field_list_filter_class(field, request, lookup_params,
                        self.model, self, field_path=field_path)

                if spec and spec.has_output():
                    filter_specs.append(spec)

        return filter_specs

    def get_query_string(self, new_params=None, remove=None):
        """ pulled from the changelist object in the django admin """

        if new_params is None:
            new_params = {}

        if remove is None:
            remove = []

        p = dict(self.request.GET.items())
        for r in remove:
            for k in p.keys():
                if k.startswith(r):
                    del p[k]

        for k, v in new_params.items():
            if v is None:
                if k in p:
                    del p[k]
            else:
                p[k] = v

        return '?' + urlencode(p)

    def get_filtered_queryset(self, queryset=None):
        if not queryset:
            queryset = super(FilterMixin, self).get_queryset(queryset)

        if not self.original_queryset:
            self.original_queryset = queryset

        self.filters = self.get_filter_classes()

        for f in self.filters:
            queryset = f.queryset(self.request, queryset)
            f.items = f.choices(self)

        return queryset

    def get_queryset(self, queryset=None):
        return self.get_filtered_queryset(queryset)

    def get_context_data(self, **kwargs):
        kwargs['original_queryset'] = kwargs.get("original_queryset", self.original_queryset)
        return super(FilterMixin, self).get_context_data(
            filters=getattr(self, "filters", []),
            **kwargs)
