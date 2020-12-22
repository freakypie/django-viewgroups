from django.db.models.query_utils import Q
import operator

from .base import SessionDataMixin
from six.moves import reduce


class SearchMixin(SessionDataMixin):
    search_fields = []
    search_term = "q"
    allow_empty_search = True
    ordering = []
    original_queryset = None

#     def get_used_parameters(self, *args):
#         return super(SearchMixin, self).get_used_parameters(self.search_term, *args)

    def get_search_fields(self):
        return getattr(self, "search_fields", [])

    def get_query(self):
        data = self.get_data()
        return data.get(self.search_term, "")

    def perform_search(self, queryset):

        self.query = self.get_query()
        terms = self.query.split()
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

    def get_searched_queryset(self, queryset=None):
        if queryset is None:
            queryset = super(SearchMixin, self).get_queryset(queryset)

        if not self.original_queryset:
            self.original_queryset = queryset

        queryset = self.perform_search(queryset)
        return queryset

    def get_queryset(self, queryset=None):
        return self.get_searched_queryset(queryset)

    def is_empty_search(self):
        return not self.request.REQUEST.get(self.search_term, None)

    def get_context_data(self, **kwargs):
        query = getattr(self, "query", "")
        if query:
            kwargs['original_queryset'] = kwargs.get("original_queryset", self.original_queryset)
        return super(SearchMixin, self).get_context_data(
            query=query,
            search=self.get_search_fields() and self.search_term,
            **kwargs
        )
