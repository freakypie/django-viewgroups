from django.db.models import Q
from django.http import HttpResponse
from django.views.generic.base import View
from django.views.generic.list import MultipleObjectMixin
from viewsets import ViewSetMixin
import json
import operator


class SearchMixin(object):
    search_fields = None
    search_term = "q"
    allow_empty_search = True
    ordering = []

    def get_search_fields(self):
        return getattr(self, "search_fields")

    def get_query(self, data):
        return data.get(self.search_term, "")

    def get_terms(self, data):
        self.query = self.get_query(data)
        return self.query.split()

    def get_search_data(self):
        return self.request.REQUEST.copy()

    def perform_search(self, queryset):
        self.query = ""
        data = self.get_search_data()
        terms = self.get_terms(data)
        fields = self.get_search_fields()

        if fields and terms:
            for term in terms:
                filters = [Q(**{field + "__icontains": term}) for field in fields]
                queryset = queryset.filter(reduce(operator.or_, filters))

        # if hitting page with an empty get request return an empty queryset
        if not self.allow_empty_search and self.is_empty_search():
            queryset = self.model.objects.none()

        queryset.searched = True

        return queryset

    def get_queryset(self, queryset=None):
        queryset = super(SearchMixin, self).get_queryset()

        queryset = self.perform_search(queryset)

        return queryset

    def is_empty_search(self):
        return not self.request.REQUEST.get(self.search_term, None)

    def get_context_data(self, **kwargs):
        return super(SearchMixin, self).get_context_data(
            query=getattr(self, "query", None),
            **kwargs
        )


class AutocompleteView(ViewSetMixin, SearchMixin, MultipleObjectMixin, View):
    paginate_by = 15

    def label_from_instance(self, instance):
        return u"%s" % instance

    def dict_from_instance(self, instance):
        return dict(
            text=self.label_from_instance(instance),
            id=instance.pk
        )

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        if not hasattr(queryset, 'searched'):
            queryset = self.perform_search(queryset)
        page_size = self.get_paginate_by(queryset)

        return HttpResponse(json.dumps(
            [self.dict_from_instance(p) for p in queryset[:page_size]]
        ))
