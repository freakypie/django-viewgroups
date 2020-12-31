# this is not complete ~ May 7th, 2013 JL
from django.views.generic.edit import CreateView
from django.forms.models import modelform_factory, inlineformset_factory, \
    BaseInlineFormSet, ModelForm, _get_foreign_key, modelformset_factory
from django.template.loader import render_to_string
from django.contrib.contenttypes.forms import generic_inlineformset_factory
from django.shortcuts import redirect
from django.utils.translation import ugettext_lazy as _


class Inline(object):
    model = None
    formset_kwargs = {"can_delete": True, "extra": 1}
    form_kwargs = {}
    form_class = None
    formset_class = None

    def __init__(
        self, model, form=None, formset_class=None,
        template="forms/inline.html", **kwargs
    ):

        self.model = model
        self.opts = self.model._meta
        self.template = template

        self.form_class = form
        self.formset_class = formset_class
        self.form_kwargs = self.form_kwargs.copy()
        self.formset_kwargs = self.formset_kwargs.copy()
        self.formset_kwargs.update(kwargs)

    def get_form_class(self, request, instance=None, **kwargs):
        kwargs.update(self.form_kwargs)
        if "exclude" in self.formset_kwargs:
            kwargs['exclude'] = kwargs.get("exclude", []) \
                + self.formset_kwargs.get("exclude")

        try:
            fk = _get_foreign_key(type(self.instance), self.model)
            kwargs['exclude'] = kwargs.get("exclude", []) + [fk.name]
        except:
            pass

        return modelform_factory(self.model, form=self.form_class or ModelForm,
            **kwargs)

    def get_headers(self):
        form = self.get_form_class(self.request, self.instance)()

        for field in form.visible_fields():
            name = field.name.replace("_", " ").title()
            yield _(name)

    def prepare(self, request, instance):
        self.request = request
        self.instance = instance

        args = []
        if request.method == "POST":
            args.append(request.POST)
            args.append(request.FILES)

        formset_class = self.create_formset_class(instance)

        self.create_formset(args, instance, formset_class)

        return self

    def create_formset(self, args, instance, formset_class):
        self.formset = formset_class(*args, instance=instance)

    def create_formset_class(self, instance):
        return inlineformset_factory(type(instance), self.model,
            formset=self.formset_class or BaseInlineFormSet,
            form=self.get_form_class(self.request, instance),
            **self.formset_kwargs)

    def __unicode__(self):
        return render_to_string(
            self.template,
            {
                "formset": self.formset,
                "title": self.opts.verbose_name_plural.title,
                "inline": self,
            }
        )


class GenericInline(Inline):
    exclude_names = ["content_type", "object_id"]

    def create_formset_class(self, instance):
        return generic_inlineformset_factory(self.model,
            form=self.get_form_class(self.request, instance),
            **self.formset_kwargs)

    def get_headers(self):
        form = self.get_form_class(self.request, self.instance,
            exclude=self.exclude_names)()

        for field in form.visible_fields():
            name = field.name.replace("_", " ").title()
            yield _(name)


class FormsetInline(Inline):
    exclude_names = []

    def create_formset_class(self, instance):
        return modelformset_factory(self.model,
            form=self.get_form_class(self.request, instance),
            **self.formset_kwargs)

    def get_headers(self):
        form = self.get_form_class(self.request, self.instance,
            exclude=self.exclude_names)()

        for field in form.visible_fields():
            name = field.name.replace("_", " ").title()
            yield _(name)

    def create_formset(self, args, instance, formset_class):
        self.formset = formset_class(*args, queryset=self.model.objects.none())


class ModelFormWithInlinesView(CreateView):
    """ creates or updates an object

    if a pk is provided then it will get and update the object
    otherwise an object will be created
    """
    inlines = []
    fields = '__all__'

    def get_inlines(self):
        return self.inlines

    def new_object(self):
        return self.get_queryset().model()

    def get_object(self, queryset=None):
        try:
            return super(ModelFormWithInlinesView, self).get_object()
        except AttributeError:
            return self.new_object()

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.created = self.object.id is None

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        inlines = self.get_inlines()
        [k.prepare(self.request, self.object) for k in inlines]

        return self.render_to_response(self.get_context_data(
            form=form,
            inlines=inlines
        ))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.created = self.object.id is None

        form_class = self.get_form_class()
        form = self.get_form(form_class)

        inlines = self.get_inlines()
        [k.prepare(self.request, self.object) for k in inlines]

        valid = form.is_valid()
        for inline in inlines:
            if not inline.formset.is_valid():
                valid = False

        if valid:
            return self.form_valid(form, inlines)
        else:
            return self.form_invalid(form, inlines)

    def form_valid(self, form, inlines):

        self.object = form.save()
        if hasattr(form, "save_m2m"):
            form.save_m2m()

        for inline in inlines:
            inline.formset.save()

        return redirect(self.get_success_url())

    def form_invalid(self, form, inlines):
        return self.render_to_response(self.get_context_data(
            form=form, inlines=inlines))
