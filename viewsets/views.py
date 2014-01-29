from django.db.models import Q
from django.http import HttpResponse
from django.views.generic.base import View, TemplateView
from django.views.generic.list import ListView, MultipleObjectMixin
import json
import operator
from django.views.generic.detail import DetailView, SingleObjectMixin
import traceback


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
        called when a form is submitted
        (it's key must be in the response) and valid
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
            print key, form
            if form.is_bound:
                print "form is bound"
                if form.is_valid():
                    print "form is valid"
                    response = self.form_valid(key, form)
                else:
                    print "form is not valid"
                    response = self.form_invalid(key, form)
                    print form.errors.as_text()
                if isinstance(response, HttpResponse):
                    print "responded"
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

