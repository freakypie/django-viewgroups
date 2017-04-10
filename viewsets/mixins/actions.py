from collections import OrderedDict as SortedDict

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _


class NoActionFound(Exception):
    pass


class ActionMixin(object):
    """
    allows the view to perform actions on list items
    This view expects `get_queryset` to be present
    """
    action_name = "action"
    selected_name = "selected"
    actions = []  # ['delete_selected']
    delete_selected_template = "base/actions/delete_selected.html"

    # you can provide your own with a mixin or by extending your class
    def delete_selected(self, request, queryset):
        if "confirmed" in request.POST:
            for obj in queryset:
                # calling individual deletes so triggers will run
                obj.delete()
            return redirect(".")
        return render(request, self.delete_selected_template, {
            "selected_name": self.selected_name,
            "action_name": self.action_name,
            "action": request.REQUEST.get(self.action_name),
            "queryset": queryset,
            "opts": queryset.model._meta
        })
    delete_selected.short_description = _("Delete selected %(verbose_name_plural)s")

    def get_actions(self):
        return self.actions

    def get_action(self, name):
        if callable(name):
            return name.__name__, name
        elif hasattr(self, name):
            return name, getattr(self, name)
        else:
            raise NoActionFound()

    def prepare_actions(self):
        self.action_list = SortedDict()
        for action in self.get_actions():
            try:
                slug, func = self.get_action(action)
            except NoActionFound:
                continue
            if hasattr(func, "short_description"):
                title = func.short_description % {
                    "verbose_name": force_text(self.model._meta.verbose_name),
                    "verbose_name_plural": force_text(self.model._meta.verbose_name_plural)
                }
            else:
                title = slug.title().replace("_", " ")

            self.action_list[slug] = (title, func)

        return self.action_list

    def get_context_data(self, **kwargs):

        if not hasattr(self, "action_list"):
            self.action_list = self.prepare_actions()

        actions = [(k, a[0]) for k, a in self.action_list.items()]

        return super(ActionMixin, self).get_context_data(
            action_name=self.action_name,
            selected_name=self.selected_name,
            actions=actions,
            **kwargs)

    def get_action_queryset(self, action):
        if self.request.POST.get("select_across"):
            queryset = self.get_queryset()
        else:
            ids = self.request.POST.getlist(self.selected_name)
            queryset = self.get_queryset().filter(id__in=ids)
        return queryset

    def perform_action(self, action):
        """
        Executes the given action and Returns None or an HttpResponse
        """
        self.action_list = self.prepare_actions()
        if action and action in self.action_list:
            title, func = self.action_list.get(action)
            queryset = self.get_action_queryset(action)
            response = func(self.request, queryset)
            if isinstance(response, HttpResponse):
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response['Pragma'] = "no-cache"
                response['Expires'] = 0
                return response
