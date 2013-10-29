# Getting Started

Import ViewSet to make a basic set of views for a particular model

.. code-block:: python

    from viewsets import ViewSet
    
    pizza_viewset = ViewSet()
    
Viewsets come with these basic views: list, create, detail, update, and delete

You can then import those views into your urls file easy. The following code
will install all of your viewsets at the default location.

.. code-block:: python

    urlpatterns = ViewSet.all_urls()

Import ViewSetMixin to use mixin with views that you are overriding

.. code-block:: python

    from viewsets import ViewSet, ViewSetMixin


Override default views or create your own with the viewset manager.
    
.. code-block:: python

    @pizza_viewset.register("create")
    class ToppingCreateView(ViewSetMixin, CreateView):
        ....

