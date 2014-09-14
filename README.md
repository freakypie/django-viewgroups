# Pre-requisites

The Default templates assume bootstrap3 and font-awesome, if you don't want to use
them you'll have to provide your own templates or modify.


# Installation

Add to settings.INSTALLED_APPS

    'viewsets' # even though in pypi, the page is django-viewgroups

You don't need to install the app except to get easy access to templates.
The default templates assume the use of Bootstrap 3, if you aren't using them
you'll have to write your own. You can copy the templates/base/ directory
in viewsets to your own project and modify them as needed,
or make your own from scratch.

# Getting Started

Import ViewSet to make a basic set of views for a particular model

    from viewsets import ViewSet
    
    pizza_viewset = ViewSet(model=Pizza)

    # or

    class PizzaViewSet(ViewSet):
        model = Pizza

    pizza_viewset = PizzaViewSet()

    
Viewsets come with these basic views: list, create, detail, update, and delete.
If you pass `exclude`, you can change that.

    pizza_viewset = ViewSet(model=Pizza, exclude=["delete"]) # don't delete pizza

You can then import those views into your urls file easy. The following code
will install all of your viewsets at the default location.

    urlpatterns = ViewSet.all_urls()

Import ViewSetMixin to use mixin with views that you are overriding

    from viewsets import ViewSet, ViewSetMixin


Override default views or create your own with the viewset manager.
    
    @pizza_viewset.register("create")
    class ToppingCreateView(ViewSetMixin, CreateView):
        ....


# Templates

Viewsets were made to give you a place for everything by convention.
Mostly based on the model name (but you can configure it on the ViewSet object)
and then the action you want to perform.

View templates will be in `templates/base`, but you can override them with a model
specific name. For instance, if you have a Pizza model, you can override them at
`templates/pizzas` (notice that it is plural).

Inside of the `pizzas` folder, you can override views based on their name.
i.e: create, update, detail, list, etc


# Template Links

Using Pizza as an example again, you can make links with a convention similar to
the template structure. For instance, if you want to link to a pizza's detail page

    {% url 'pizzas:detail' %}

If you create a custom view, just use the name you register the view with.
