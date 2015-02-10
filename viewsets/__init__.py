from copy import copy, deepcopy
from django.conf import settings
from django.conf.urls import patterns, include
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.template.defaultfilters import slugify
from django.utils.datastructures import SortedDict
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from viewsets.views import FilterMixin, SearchMixin, AdminListView
import os
import six

from viewsets.mixins.manager import ViewSetMixin
from viewsets.mixins.sort import SortMixin


class NoDetailMixin(object):

    def get_success_url(self):
        return reverse("base:list", current_app=self.manager.name)


class ViewSetCreateView(ViewSetMixin, CreateView):
    pass


class ViewSetUpdateView(ViewSetMixin, UpdateView):
    pass


class ViewSetDeleteView(ViewSetMixin, DeleteView):

    def get_success_url(self):
        return reverse(self.manager.default_app + ":list",
            current_app=self.manager.name)


class ViewSetListView(ViewSetMixin, AdminListView):
    paginate_by = 25


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
                if name in ("update", "delete", ):
                    self.instance_view(name, ordering=ordering)(view)
                elif name in ("list", ):
                    self.register(name, url=r'^$', ordering=ordering, links=[])(view)
                elif name in ("detail", ):
                    self.register(name, url=r'^%s$' % self.object_url, links=[])(view)
                else:
                    self.register(name, ordering=ordering)(view)

        if template_dir:
            self.template_dir = template_dir
        elif not self.template_dir:
            self.template_dir = self.name

        ViewSet._managers.append(self)

    def get_base_url(self):
        return self.base_url or "{}/".format(self.name)

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

            for link in links:
                if link in self.links:
                    self.links[link].append(view)
                else:
                    self.links[link] = [view]

#             view.name = name
#             view.manager = self
            view = view.as_view(**kwargs)
            urls.append((url_regex, view, {}, name))

        return patterns('', *urls), self.default_app, self.name

    @classmethod
    def all_urls(klass):
        urls = []
        for m in klass.managers:
            urls.append((m.get_base_url(), include(m.get_urls())))
        return patterns('', *urls)

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
            self.views.keyOrder.remove(name)
            self.views.keyOrder.insert(ordering, name)
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
