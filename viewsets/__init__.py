import os

from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.conf.urls import patterns, include
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.conf import settings
from django.template.defaultfilters import slugify
from django.utils.datastructures import SortedDict
from viewsets.views import MiningListView
from copy import copy, deepcopy
import six


class ViewSetMixin(object):

    def get_context_data(self, **kwargs):
        context = super(ViewSetMixin, self).get_context_data(**kwargs)
        if getattr(self, "manager", None):
            context.update(self.manager.extra_context(self.request, self))
        return context

    # need to set the current app for url namespace resolution
    def render_to_response(self, context, **response_kwargs):
        if getattr(self, "manager", None):
            response_kwargs["current_app"] = self.manager.name
            context.update({"current_app": self.manager.name})

        return super(ViewSetMixin, self).render_to_response(context, **response_kwargs)

    def get_success_url(self):
        return reverse(self.manager.default_app + ":detail", args=[self.object.id],
            current_app=self.manager.name)

    def get_template_names(self):
        template_name = getattr(self, "template_name", None)
        if template_name:
            return template_name

        templates = [
            [
                self.manager.base_template_dir,
                self.manager.template_dir,
                self.name + ".html"
            ],
            [
                self.manager.base_template_dir,
                self.manager.default_app,
                self.name + ".html"
            ]
        ]

        if self.request.is_ajax():
            ajax_templates = deepcopy(templates)
            for template in ajax_templates:
                template[-1] = self.name + "_ajax.html"
            templates = ajax_templates + templates

        return [os.path.join(*bits) for bits in templates]

    def get_queryset(self):
        return self.manager.get_queryset(self, self.request, **self.kwargs)


class ViewSetCreateView(ViewSetMixin, CreateView):
    pass


class ViewSetUpdateView(ViewSetMixin, UpdateView):
    pass


class ViewSetDeleteView(ViewSetMixin, DeleteView):

    def get_success_url(self):
        return reverse(self.manager.default_app + ":list",
            current_app=self.manager.name)


class ViewSetListView(ViewSetMixin, MiningListView):
    paginate_by = 25


class ViewSetDetailView(ViewSetMixin, DetailView):
    pass


class classproperty(property):
    def __get__(self, cls, owner):
        return self.fget.__get__(None, owner)()


class ViewSet(object):
    PK_URL = "(?P<pk>\d+)/"
    SLUG_URL = "(?P<slug>[\w\-\d]+)/"

    mixin = None
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

    def __init__(self, name=None, model=None, template_dir=None, exclude=None):

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

        if self.base_url is None:
            self.base_url = "^%s/" % self.name

        self.views = SortedDict((
            ("create", (ViewSetCreateView, r'^create/$')),
            ("update", (ViewSetUpdateView, r'^%supdate/$' % self.object_url)),
            ("delete", (ViewSetDeleteView, r'^%sdelete/$' % self.object_url)),
            ("detail", (ViewSetDetailView, r'^%s$' % self.object_url)),
            ("list", (ViewSetListView, r'^$')),
        ))

        for name in self.exclude:
            del self.views[name]

        if template_dir:
            self.template_dir = template_dir
        elif not self.template_dir:
            self.template_dir = self.name

        ViewSet._managers.append(self)

    @classproperty
    @classmethod
    def managers(klass):
        for m in klass._managers:
            if isinstance(m, klass):
                yield m

    def pre_dispatch(self, request, view, **kwargs):
        pass

    def get_urls(self):
        urls = []
        for name, (view_class, url_regex) in self.views.items():
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
                    

#             view.name = name
#             view.manager = self
            view = view.as_view(**kwargs)
            urls.append((url_regex, view, {}, name))

        return patterns('', *urls), self.default_app, self.name

    @classmethod
    def all_urls(klass):
        urls = []
        for m in klass.managers:
            urls.append((m.base_url, include(m.get_urls())))
        return patterns('', *urls)

    def get_queryset(self, view, request, **kwargs):
        return self.model.objects.all()

    def register(self, name, url=None, ordering=0):
        """ use this to decorate your views """

        if not url:
            if name in self.views:
                url = self.views[name][1]
            else:
                url = r'^%s/$' % (name)

        def inner(view):
            self.views[name] = (view, url)
            self.views.keyOrder.remove(name)
            self.views.keyOrder.insert(ordering, name)
            return view

        return inner

    def instance_view(self, name):
        return self.register(name,
            r'^%s%s/$' % (self.object_url, name))

    def extra_context(self, request, view, **kwargs):
        return dict(
            manager=self,
            opts=self.model._meta,
            **kwargs
        )
