from django.core.paginator import InvalidPage
from django.http import HttpResponse, Http404
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import View, TemplateView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.list import ListView, MultipleObjectMixin
import json

from viewsets.mixins.actions import ActionMixin
from viewsets.mixins.filter import FilterMixin
from viewsets.mixins.search import SearchMixin
from viewsets.mixins.sort import TableMixin


class AutocompleteMixin(SearchMixin):

    def label_from_instance(self, instance):
        return u"%s" % instance

    def dict_from_instance(self, instance):
        return dict(
            text=self.label_from_instance(instance),
            id=instance.pk
        )

    def to_json(self, queryset=None):
        if not queryset:
            queryset = self.get_queryset()
            if not hasattr(queryset, 'searched'):
                queryset = self.perform_search(queryset)
            page_size = self.get_paginate_by(queryset)

        return json.dumps(
            [self.dict_from_instance(p) for p in queryset[:page_size]]
        )


class AutocompleteView(AutocompleteMixin, MultipleObjectMixin, View):
    paginate_by = 15

    def get(self, request, *args, **kwargs):
        return HttpResponse(self.to_json())


class AutocompleteListView(AutocompleteMixin, ListView):
    paginate_by = 15

    def get(self, request, *args, **kwargs):
        if request.is_ajax():
            return HttpResponse(self.to_json())

        return super(AutocompleteListView, self).get(request, *args, **kwargs)


class ActionListView(ActionMixin, ListView):
    page_kwarg = 'page'

    def paginate_queryset(self, queryset, page_size):
        paginator = self.get_paginator(queryset, page_size, allow_empty_first_page=self.get_allow_empty())
        page_kwarg = self.page_kwarg
        page = self.kwargs.get(page_kwarg) or self.request.GET.get(page_kwarg) or 1
        try:
            page_number = int(page)
        except ValueError:
            if page == 'last':
                page_number = paginator.num_pages
            else:
                raise Http404(_("Page is not 'last', nor can it be converted to an int."))
        try:
            page = paginator.page(page_number)
        except InvalidPage:
            page = paginator.page(1)

        return (paginator, page, page.object_list, page.has_other_pages())

    def post(self, request, *args, **kwargs):

        self.object_list = self.get_queryset()

        # execute action?
        # must be before list editable which will always activate
        # if it is set.
        if self.action_name in request.POST:
            action = self.request.POST.get(self.action_name, None)
            retval = self.perform_action(action)
            if retval:
                return retval

        context = self.get_context_data(
            object_list=self.object_list,
        )

        return self.render_to_response(context)


class AdminListView(FilterMixin, SearchMixin, TableMixin, ActionListView):
    paginate_by = 25


class MultipleFormsMixin(object):
    """ processes multiple forms by key """
    form_classes = {}

    def get_form_classes(self):
        """ returns a dictionary of all form classes """
        return self.form_classes

    def get_form_kwargs(self, key, form_class, **kwargs):
        """ returns all arguments for a given form """
        kwargs['prefix'] = key
        if key in self.request.POST:
            kwargs["data"] = self.request.POST
            kwargs["files"] = self.request.FILES
        return kwargs

    def get_forms(self):
        """ returns dictionary of form instances for all form classes """
        forms = {}
        for key, form_class in self.get_form_classes().items():
            forms[key] = self.get_form(key, form_class)
        return forms

    def get_form(self, key, form_class):
        """ gets an individual form instance """
        return form_class(**self.get_form_kwargs(key, form_class))

    def form_valid(self, key, form):
        """
        called when a form is submitted and valid
        (it's key must be in the request)
        """
        pass

    def form_invalid(self, key, form):
        """ called when a form is submitted but not valid """
        pass

    def process_forms(self, forms):
        """ checks all forms to see if one was submitted
            will return a HttpResponse or None
        """
        for key, form in forms.items():
            if form.is_bound:
                if form.is_valid():
                    response = self.form_valid(key, form)
                else:
                    response = self.form_invalid(key, form)
                if isinstance(response, HttpResponse):
                    return response
        return None


class MultipleFormView(MultipleFormsMixin, TemplateView):

    def dispatch(self, request, *args, **kwargs):
        return TemplateView.dispatch(self, request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self.get_context_data(forms=self.get_forms()))

    def post(self, request, *args, **kwargs):
        forms = self.get_forms()
        response = self.process_forms(forms)

        if response:
            return response
        return self.render_to_response(self.get_context_data(forms=forms))

    def get_context_data(self, **kwargs):
        return kwargs


class MultipleFormDetailView(SingleObjectMixin, MultipleFormView):

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(MultipleFormDetailView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super(MultipleFormDetailView, self).post(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return super(MultipleFormDetailView, self).get_context_data(
            object=self.object,
            **kwargs
        )
