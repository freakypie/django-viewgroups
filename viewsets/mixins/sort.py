from django.core.urlresolvers import reverse
from django.db.models.fields.related import ReverseSingleRelatedObjectDescriptor
from django.utils.encoding import StrAndUnicode
from django.utils.safestring import mark_safe

from viewsets.mixins.base import SessionDataMixin


class Header(StrAndUnicode):

    def __init__(self, title, sort_field=None, sorting=0, link=None, sort_name="sort"):
        self.title = title
        self.sort_field = sort_field
        self.sorting = sorting
        self.link = link
        self.sort_name = sort_name

    @property
    def link_tag(self):
        if self.sort_field:
            if self.sorting == 0:
                retval = '<a href="?%s=%s">%s</a>' % (self.sort_name, self.sort_field, self.title)
            elif self.sorting == 1:
                retval = '<a href="?%s=-%s">%s <i class="glyphicon glyphicon-chevron-down"></i></a>' % (self.sort_name, self.sort_field, self.title)
            else:
                retval = '<a href="?%s=">%s <i class="glyphicon glyphicon-chevron-up"></i></a>' % (self.sort_name, self.title)
        else:
            retval = self.title

        return mark_safe(retval)

    def __unicode__(self):
        return self.link_tag


class SortMixin(SessionDataMixin):
    sort_term = "sort"
    sort_fields = ["id"]
    ordering = ["id"]

    def get_sort_fields(self):
        """
        returns a list of fields to sort by
        fields can be prefixed with '-' to indicate descending
        like the django order_by syntax
        """
        data = self.get_data()
        return data.get(self.sort_term, "").split(",")

    def get_allowed_sort_fields(self, model):
        return getattr(self, "sort_fields")

    def get_sorted_queryset(self, queryset=None):
        """
        filters the given sort fields from the user and sends on
        those that are allowed on the headers.
        """
        if queryset is None:
            queryset = super(SortMixin, self).get_queryset(queryset)

        sort_terms = self.get_sort_fields()
        if sort_terms:
            allowed_fields = list(self.get_allowed_sort_fields(queryset.model))

            sort_fields = []
            for sort in sort_terms:
                sort = sort.strip()

                # strip minus prefix
                desc = False
                if sort.startswith("-"):
                    desc = True
                sort = sort.lstrip("-")

                if sort in allowed_fields:
                    sort_fields.append(desc and "-" + sort or sort)
        else:
            sort_fields = self.ordering

        if sort_fields:
            self.sorting_fields = sort_fields
            queryset = queryset.order_by(*sort_fields)
        else:
            self.sorting_fields = []

        return queryset

    def get_queryset(self, queryset=None):
        return self.get_sorted_queryset(queryset)

    def get_context_data(self, **kwargs):
        return super(SortMixin, self).get_context_data(
            sort_name=self.sort_term,
            sorting_fields=getattr(self, "sorting_fields", []),
            **kwargs)


class TableMixin(SortMixin):
    """ causes views with a list to have enough context to make a table """
    list_display = ["__unicode__"]
    list_display_links = []
    list_editable = None  # NOT Implemented
    list_detail_link = ""

    def get_allowed_sort_fields(self, model):
        self._list_display = self.get_list_display()
        for field in self._list_display:
            if callable(field):
                sort = getattr(field, "sort_field", field)
                if sort:
                    yield sort
            elif isinstance(field, basestring) and not "__" in field:
                retval = model._meta.get_field_by_name(field)
                if retval:
                    yield field

    def get_list_display(self, fields=None):
        """ get the fields to display """

        if not fields:
            fields = getattr(self, "list_display")

        retval = []
        for field in fields:
            if field not in ("__unicode__",) and hasattr(self, field):
                retval.append(getattr(self, field))
            else:
                retval.append(field)

        return retval

    def get_detail_link(self, obj):
        name = getattr(self, "list_detail_link")
        if name:
            return reverse(name, args=[obj.id])
        return ""

    def get_list_display_links(self):
        return getattr(self, "list_display_links")

    def get_headers(self, object_list, list_display):
        """ requires that self.object_list is set before called """

        if object_list is None:
            object_list = self.object_list

        for field in list_display:

            sort_field = field
            if field == "__unicode__":
                # unicode default
                retval = object_list.model._meta.verbose_name
                sort_field = ":default:"

            elif callable(field):
                retval = field

            elif isinstance(field, basestring):
                if hasattr(self, field):
                    # view field
                    retval = getattr(self, field, None)

                else:
                    # model field
                    retval = self.object_list.model
                    for subfield in field.split("__"):
                        item = getattr(retval, subfield, None)

                        if isinstance(item, ReverseSingleRelatedObjectDescriptor):
                            item = item.get_query_set().model

                        if not item:
                            try:
                                # if its a field, then get it's verbose name
                                item = retval._meta.get_field(subfield).verbose_name.title()
                            except Exception:
                                pass

                        retval = item

                        if not retval:
                            break

            if callable(retval):
                sort_field = None

                if hasattr(retval, "short_description"):
                    retval = retval.short_description
                else:
                    retval = retval.__name__.replace("_", " ").title()

                if hasattr(field, "sort_field"):
                    sort_field = field.sort_field

            if sort_field in self.sorting_fields:
                sorting = 1
            elif "-%s" % sort_field in self.sorting_fields:
                sorting = -1
            else:
                sorting = 0

            yield Header(u"%s" % retval, sort_field, sorting)

    def get_rows(self, object_list, list_display):
        if object_list is None:
            object_list = self.object_list
        for obj in object_list:
            yield obj, self.get_row(obj, list_display)

    def get_row(self, obj, list_display):
        for name, cell in self.get_cells(obj, list_display):
            if name in self.get_list_display_links():
                cell = "<a href='%s'>%s</a>" % (self.get_detail_link(obj), cell)

            yield mark_safe(cell)

    def get_cells(self, obj, list_display):
        for idx, field in enumerate(list_display):
            try:
                if callable(field):
                    retval = field(obj)
                    field = getattr(field, "short_description", field.__name__)
                else:
                    retval = obj
                    if field == "__unicode__":
                        retval = getattr(retval, field, None)
                    else:
                        for bit in field.split("__"):
                            retval = getattr(retval, bit, None)
                            if retval is None:
                                break  # we tried

                    if callable(retval):
                        retval = retval()
            except Exception, ex:
                retval = "_"

            if retval is None:
                retval = "_"

            yield field, retval

    def get_context_data(self, **kwargs):
        list_display = self.get_list_display()
        context = super(TableMixin, self).get_context_data(
            list_display=list_display,
            list_display_links=self.get_list_display_links(),
            **kwargs)
        object_list = context.get("object_list")
        context.update(
            headers=self.get_headers(object_list, list_display),
            rows=self.get_rows(object_list, list_display)
        )
        return context
#
#        if self.list_editable:
#            context['formset'] = self.get_formset()
#
#        # list is a form
#        if self.list_editable:
#            formset = self.get_formset()
#            if self.request.method == "POST":
#                if formset.is_valid():
#                    return self.formset_valid(formset)
#        else:
#            formset = None
#
#    def get_formset_kwargs(self, **kwargs):
#        kwargs.setdefault("queryset", self.object_list)
#        if self.request.method == "POST":
#            kwargs.update(
#                data=self.request.POST,
#                files=self.request.FILES,
#            )
#        return kwargs
#
#    def get_formset_class(self):
#        return modelformset_factory(
#            fields=self.list_editable,
#            extra=getattr(self, "extra", 0),
#            model=self.object_list.model
#        )
#
#    def get_formset(self):
#        return self.get_formset_class()(**self.get_formset_kwargs())
#
#    def formset_valid(self, formset):
#        """ override this to have if you have list editable """
#        formset.save()
#        return redirect('.')
