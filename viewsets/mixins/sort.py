from __future__ import print_function

import six
from django.db import models
from django.db.models.base import ModelBase
from django.db.models.fields import FieldDoesNotExist
from django.urls import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext as _

from .base import SessionDataMixin


@python_2_unicode_compatible
class Header(object):

    def __init__(self, title, sort_field=None, sorting=0, link=None, sort_name="sort"):
        if title:
            self.title = _(title)
        else:
            self.title = ""
        self.sort_field = sort_field
        self.sorting = sorting
        self.link = link
        self.sort_name = sort_name

    @property
    def link_tag(self):
        if self.sort_field:
            if self.sorting == 0:
                retval = '<a href="?%s=%s">%s</a>' % (self.sort_name, self.sort_field, self.proper_title)
            elif self.sorting == 1:
                retval = '<a href="?%s=-%s">%s <i class="glyphicon glyphicon-chevron-down"></i></a>' % (self.sort_name, self.sort_field, self.proper_title)
            else:
                retval = '<a href="?%s=">%s <i class="glyphicon glyphicon-chevron-up"></i></a>' % (self.sort_name, self.proper_title)
        else:
            retval = self.proper_title
        return retval

    @property
    def proper_title(self):
        return self.title.replace('_', ' ')

    def __str__(self):
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

        sort_fields = self.ordering
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


class TableField(object):

    def __init__(self, view, field):
        self.view = view
        self.field = field
        self.original = self.field

    def __str__(self):
        return "{}: {}".format(type(self), self.field)

    def header(self):
        return self.field

    def sort(self):
        return None

    def value(self, instance):
        return six.text_type(instance)


class UnicodeTableField(TableField):

    def valid(self):
        return self.field == "__str__" or self.field == "__str__"

    def header(self):
        try:
            return self.view.model._meta.verbose_name
        except AttributeError:
            return ""

    def sort(self):
        return ""


class CallableTableField(TableField):

    def valid(self):
        return callable(self.field)

    def header(self):
        return getattr(self.field, "short_description",
            self.field.__name__.replace("_", " ").title())

    def sort(self):
        return getattr(self.field, "sort_field", None)

    def value(self, instance):
        if hasattr(self.field, "requires_request"):
            return self.field(self.view.request, instance)
        return self.field(instance)


class ViewCallableTableField(CallableTableField):

    def valid(self):
        if isinstance(self.field, six.string_types):
            self.field = getattr(self.view, self.field, None)
            return self.field is not None
        return False


class ManagerCallableTableField(CallableTableField):

    def valid(self):
        manager = getattr(self.view, "manager", None)
        if manager and isinstance(self.field, six.string_types):
            self.field = getattr(manager, self.field, None)
            return self.field is not None
        return False


class ModelTableField(CallableTableField):
    is_model_field = False

    def valid(self):
        if isinstance(self.field, six.string_types):
            field = self.view.model
            for subfield in self.field.split("__"):
                item = None

                if isinstance(field, ModelBase):
                    item = field._meta.get_field(subfield)

                    if getattr(item, 'related_model', None):
                        item = item.related_model

                    else:
                        try:
                            if hasattr(item, 'get_queryset'):
                                item = item.get_queryset().model
                        except (Exception, FieldDoesNotExist):
                            pass

                        if not item:
                            try:
                                # if its a field, then get it's verbose name
                                item = field._meta.get_field(subfield).verbose_name
                                self.is_model_field = True
                            except (AttributeError, FieldDoesNotExist):
                                pass

                field = item

                if not field:
                    break

            self.attr = field

            return self.attr is not None
        return False

    def header(self):
        return getattr(self.attr, "short_description", None) or \
            getattr(self.attr, "name", None) or \
            self.field.title()

    def sort(self):
        if self.is_model_field:
            return self.field
        else:
            return getattr(self.field, "sort_field", None)

    def value(self, instance):
        retval = instance
        for bit in self.field.split("__"):
            retval = getattr(retval, bit, None)
            if retval is None:
                break  # we tried

        if callable(retval):
            retval = retval()

        return retval


class TableMixin(SortMixin):
    """ causes views with a list to have enough context to make a table """
    list_display = ["__str__"]
    list_display_links = []
    list_editable = None  # NOT Implemented
    list_detail_link = ""
    field_sources = [UnicodeTableField, CallableTableField, ModelTableField,
        ViewCallableTableField, ManagerCallableTableField]

    def get_allowed_sort_fields(self, model):
        self._list_display = self.prepare_list_display()
        for field in self._list_display:
            sort_field = field.sort()
            if sort_field:
                yield sort_field

    def get_list_display(self):
        return getattr(self, "list_display")

    def get_detail_link(self, obj):
        name = getattr(self, "list_detail_link")
        if name:
            return reverse(name, args=[obj.id])
        return ""

    def get_list_display_links(self):
        return getattr(self, "list_display_links")

    def prepare_list_display(self):
        retval = []
        for field in self.get_list_display():
            for source in self.field_sources:
                column = source(self, field)
                if column.valid():
                    retval.append(column)
                    break

        return retval

    def get_headers(self, object_list, list_display):
        """ requires that self.object_list is set before called """

        for field in list_display:
            sort_field = field.sort()
            sorting = 0
            if sort_field:
                if sort_field in self.sorting_fields:
                    sorting = 1
                elif "-%s" % sort_field in self.sorting_fields:
                    sorting = -1

            yield Header(field.header(), sort_field, sorting)

    def get_rows(self, object_list, list_display):
        for obj in object_list:
            yield obj, self.get_row(obj, list_display)

    def get_row(self, obj, list_display):
        list_display_links = self.get_list_display_links()
        for name, cell in self.get_cells(obj, list_display):
            if cell == '':
                # if the the list_display_link is an empty string and it's the only one...
                # it makes it impossible for a user to select fixing here by adding text.
                cell = 'None'

            if name in list_display_links:
                cell = u"<a href='{}'>{}</a>".format(self.get_detail_link(obj), escape(cell))
                yield mark_safe(cell)
            else:
                yield cell

    def get_cells(self, obj, list_display):
        for field in list_display:
            try:
                retval = field.value(obj)
            except Exception as ex:
                print (type(ex), ex)
                retval = mark_safe(u"<i style='color:darkred;' " + \
                    u"class='glyphicon glyphicon-exclamation-sign' " + \
                    u"title='{}: {}'></i>".format(type(ex).__name__, escape(str(ex))))

            if retval is None:
                retval = "_"

            yield field.original, retval

    def get_context_data(self, **kwargs):
        list_display = getattr(self, "_list_display", None) or \
            self.prepare_list_display()
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
