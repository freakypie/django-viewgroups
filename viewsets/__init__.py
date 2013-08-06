import os

from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.conf.urls import patterns, include
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.conf import settings
from django.template.defaultfilters import slugify


class ViewSetMixin(object):

    def get_context_data(self, **kwargs):
        context = super(ViewSetMixin, self).get_context_data(**kwargs)
        context.update(dict(manager=self.manager, opts=self.manager.model._meta))
        return context

    # need to set the current app for url namespace resolution
    def render_to_response(self, context, **response_kwargs):
        response_kwargs["current_app"] = self.manager.name
        context.update({"current_app": self.manager.name})

        return super(ViewSetMixin, self).render_to_response(context, **response_kwargs)

    def get_success_url(self):
        return reverse(self.manager.default_app + ":detail", args=[self.object.id],
            current_app=self.manager.name)

    def get_template_names(self):
        if self.request.is_ajax():
            ajax = "_ajax"
        else:
            ajax = ""

        if self.manager.base_template_dir:
            templates = [
                "%s/%s/%s%s.html" % (
                    self.manager.base_template_dir,
                    self.manager.template_dir,
                    ajax,
                    self.name),
                "%s/%s/%s%s.html" % (
                    self.manager.base_template_dir,
                    self.manager.default_app,
                    ajax,
                    self.name)
            ]
        else:
            templates = [
                "%s/%s%s.html" % (
                    self.manager.template_dir,
                    ajax,
                    self.name),
                "%s/%s%s.html" % (
                    self.manager.default_app,
                    ajax,
                    self.name)
            ]
        return templates

    def get_queryset(self):
        return self.manager.get_queryset(self.request)


class ViewSetCreateView(ViewSetMixin, CreateView):
    pass


class ViewSetUpdateView(ViewSetMixin, UpdateView):
    pass


class ViewSetDeleteView(ViewSetMixin, DeleteView):

    def get_success_url(self):
        return reverse(self.manager.default_app + ":list",
            current_app=self.manager.name)


class ViewSetListView(ViewSetMixin, ListView):
    paginate_by = 25


class ViewSetDetailView(ViewSetMixin, DetailView):
    pass


class ViewSet(object):
    name = None
    model = None
    base_template_dir = ""
    template_dir = None
    default_app = "base"
    managers = []

    def __init__(self, name=None, model=None, template_dir=None):

        if model:
            self.model = model

        if name:
            self.name = name
        elif not self.name:
            self.name = self.model._meta.verbose_name_plural.lower()

        self.name = slugify(self.name)

        self.views = {
            "create": (ViewSetCreateView, r'^create/$'),
            "update": (ViewSetUpdateView, r'^(?P<pk>\d+)/update/$'),
            "delete": (ViewSetDeleteView, r'^(?P<pk>\d+)/delete/$'),
            "detail": (ViewSetDetailView, r'^(?P<pk>\d+)/$'),
            "list": (ViewSetListView, r'^$'),
        }

        if template_dir:
            self.template_dir = template_dir
        elif not self.template_dir:
            self.template_dir = self.name

        ViewSet.managers.append(self)

    def protect(self, function):
        if not hasattr(function, "protected"):
            def inner(self, request, *args, **kwargs):
                if not request.user.is_authenticated():
                    return redirect("%s?next=%s" % (settings.LOGIN_URL, request.path))
                return function(self, request, *args, **kwargs)
            inner.protected = True
            return inner
        return function

    def get_urls(self):
        urls = []
        for name, (view_class, url_regex) in self.views.items():
            kwargs = {}

            # override here or these views can't be used elsewhere
            # they will be slightly modified soon
            class view(view_class):
                pass

            view.dispatch = self.protect(view.dispatch)

            # preserve csrf setting
            if getattr(view_class.dispatch, "csrf_exempt", False):
                view.dispatch.__func__.csrf_exempt = True

            view.name = name
            view.manager = self
            view = view.as_view(**kwargs)
            urls.append((url_regex, view, {}, name))

        return patterns('', *urls), self.default_app, self.name

    @classmethod
    def all_urls(klass):
        urls = [("^%s/" % m.name, include(m.get_urls())) for m in klass.managers]
        return patterns('', *urls)

    def get_queryset(self, request):
        return self.model.objects.all()

    def register(self, name, url=None):
        """ use this to decorate your views """

        if not url:
            if name in self.views:
                url = self.views[name][1]
            else:
                url = r'^%s/$' % name

        def inner(view):
            self.views[name] = (view, url)
            return view

        return inner

    def instance_view(self, name):
        return self.register(name, r'^(?P<pk>\d+)/%s/$' % name)
