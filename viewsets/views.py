import json
from collections import OrderedDict as SortedDict

import six
from django.core.paginator import InvalidPage
from django.http import Http404, HttpResponse
from django.template.defaultfilters import slugify
from django.urls import include, path, re_path, reverse
from django.utils.translation import ugettext_lazy as _
from django.views.generic.base import TemplateView, View
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView, MultipleObjectMixin

from .mixins.actions import ActionMixin
from .mixins.filter import FilterMixin
from .mixins.manager import ViewSetMixin
from .mixins.search import SearchMixin
from .mixins.sort import TableMixin


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


class NoDetailMixin(object):

    def get_success_url(self):
        return reverse("base:list", current_app=self.manager.name)


class ViewSetCreateView(ViewSetMixin, CreateView):
    fields = '__all__'


class ViewSetUpdateView(ViewSetMixin, UpdateView):
    fields = '__all__'


class ViewSetDeleteView(ViewSetMixin, DeleteView):

    def get_success_url(self):
        return reverse(self.manager.default_app + ":list",
            current_app=self.manager.name)


class ViewSetListView(ViewSetMixin, AdminListView):
    pass


class ViewSetDetailView(ViewSetMixin, DetailView):
    pass


class classproperty(property):
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


class ViewSet(object):
    PK_URL = "(?P<pk>\d+)/"
    SLUG_URL = "(?P<slug>[\w\-\d]+)/"

    mixin = ViewSetMixin
    name = None
    model = None
    opts = None
    base_template_dir = ""
    base_url = None
    object_url = PK_URL
    template_dir = None
    default_app = "base"
    _managers = []
    exclude = []
    ordering = 0
    paginate_by = 25

    links = None
    default_global_link = "default_global"
    default_instance_link = "default_instance"

    def __init__(self, name=None, model=None, template_dir=None, exclude=None):

        self.links = {self.default_global_link: []}
        self.instance_links = {self.default_instance_link: []}

        if exclude:
            self.exclude = exclude

        if model:
            self.model = model

        if self.model:
            self.opts = self.model._meta

        if name:
            self.name = name
        elif not self.name:
            self.name = self.model._meta.verbose_name_plural.lower()

        self.name = slugify(self.name)

        base_url = self.get_base_url()

        self.views = SortedDict()

        for ordering, (name, view) in enumerate((
            ("list", ViewSetListView),
            ("create", ViewSetCreateView),
            ("detail", ViewSetDetailView),
            ("update", ViewSetUpdateView),
            ("delete", ViewSetDeleteView)
        )):
            if name not in self.exclude:
                if name in ("update", "delete",):
                    self.instance_view(name, ordering=ordering)(view)
                elif name in ("list",):
                    self.register(name, url=r'^$', ordering=ordering, links=[])(view)
                elif name in ("detail",):
                    self.register(name, url=r'^%s$' % self.object_url, links=[])(view)
                else:
                    self.register(name, ordering=ordering)(view)

        if template_dir:
            self.template_dir = template_dir
        elif not self.template_dir:
            self.template_dir = self.name

        ViewSet._managers.append(self)

    def get_base_url(self):
        return self.base_url or "^{}/".format(self.name)

    @classproperty
    @classmethod
    def _get_managers(klass):
        retval = []
        for m in klass._managers:
            if isinstance(m, klass):
                retval.append(m)
        return retval

    @classproperty
    @classmethod
    def managers(klass):
        return sorted(klass._get_managers, key=lambda a: (a.ordering, a.name))

    @classproperty
    @classmethod
    def managers_by_app(cls):
        return sorted(
            cls._get_managers,
            key=lambda a: (a.model._meta.app_label, a.ordering, a.name)
        )

    def pre_dispatch(self, request, view, **kwargs):
        pass

    def get_urls(self):
        urls = []

        for name, (view_class, url_regex, links) in self.views.items():
            kwargs = {}

            # override here or these views can't be used elsewhere
            # they will be slightly modified soon
            if self.mixin and not issubclass(view_class, self.mixin):
                parents = (self.mixin, view_class)
            else:
                parents = (view_class,)

            view = type(
                "%s_%s_%s" % (
                    self.__class__.__name__,
                    self.model._meta.object_name,
                    name
                ),
                parents,
                {
                    "name": name,
                    "model": self.model,
                    "manager": self
                })

            # preserve csrf setting
            if getattr(view_class.dispatch, "csrf_exempt", False):
                if six.PY3:
                    view.dispatch.csrf_exempt = True
                else:
                    view.dispatch.__func__.csrf_exempt = True

            # allow setting initialization args, kwargs
            args = getattr(view, 'initargs', None)
            initkwargs = getattr(view, 'initkwargs', None)

            if not isinstance(args, (list, tuple)):
                args = tuple()

            if isinstance(initkwargs, dict):
                kwargs.update(initkwargs)

            for link in links:
                if link in self.links:
                    self.links[link].append(view)
                else:
                    self.links[link] = [view]

#             view.name = name
#             view.manager = self
            view = view.as_view(*args, **kwargs)
            urls.append(re_path(url_regex, view, {}, name))

        return urls, self.default_app, self.name

    @classmethod
    def all_urls(klass):
        urls = []
        for m in klass.managers:
            patterns, app_name, namespace = m.get_urls()
            urls.append(re_path(m.get_base_url(), include((patterns, app_name), namespace=namespace)))
        return urls

    def get_queryset(self, view, request, **kwargs):
        return self.model.objects.all()

    def register(self, name, url=None, ordering=0, links=None):
        """ use this to decorate your views """

        if not url:
            if name in self.views:
                url = self.views[name][1]
            else:
                url = r'^%s/$' % (name)

        if links is None:
            if "P<pk>" in url or "P<slug>" in url:
                links = [self.default_instance_link]
            else:
                links = [self.default_global_link]

        def inner(view):
            self.views[name] = (view, url, links)
            # self.views.keyOrder.remove(name)
            # self.views.keyOrder.insert(ordering, name)
            return view

        return inner

    def instance_view(self, name, ordering=0, links=None):
        return self.register(name,
            r'^%s%s/$' % (self.object_url, name), ordering=ordering, links=links)

    def extra_context(self, request, view, **kwargs):
        return dict(
            manager=self,
            opts=self.model._meta,
            **kwargs
        )


