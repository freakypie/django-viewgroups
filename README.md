
# Getting Started

Import ViewSet to make a basic set of views for a particular model

    from viewsets import ViewSet
    
    pizza_viewset = PizzaViewSet()
    
You can then import those views into your urls file. The following code
will install all of your viewsets at the default location.

    urlpatterns = ViewSet.all_urls()

Import ViewSetMixin to use mixin with views that you are overriding

    from viewsets import ViewSet, ViewSetMixin


Override default views or create your own with the viewset manager.
    
    @pizza_viewset.register("create")
    class ToppingCreateView(ViewSetMixin, CreateView):
                
        ....

