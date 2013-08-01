from danemco.core.forms.fields import AutoCompleteField
from danemco.core.views.generic.inline import ModelFormWithInlinesView, Inline
from danemco.core.views.generic.search import SearchView, SearchMixin
from dispatch.models import Company, OrderMeasurement, Order, Commodity, Location, \
    WellSite
from django import forms
from django.contrib.auth.models import User
from danemco.core.forms.fields import AutoCompleteField
from dispatch.models import Company, OrderMeasurement, Driver
from django.utils import timezone
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic.base import RedirectView, TemplateView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.list import ListView
from django.contrib.auth.models import User

from .models import Order, Commodity, Location
from .viewset import ViewSet, ViewSetMixin
import random

from .viewset import ViewSet, ViewSetMixin


class BaseViewSet(ViewSet):
    default_app = "base"
    base_template_dir = "dispatch"


class HomePageView(TemplateView):
    template_name = "flatpages/home.html"

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(HomePageView, self).dispatch(request, *args, **kwargs)


class CommodityViewSet(BaseViewSet):
    model = Commodity

commodity_viewset = CommodityViewSet()
del commodity_viewset.views['delete']


#-------------------------------------------------------------------------------
# Location Views
#-------------------------------------------------------------------------------
class LocationViewSet(BaseViewSet):
    model = Location

location_viewset = LocationViewSet()
del location_viewset.views['delete']


#-------------------------------------------------------------------------------
# Driver Views
#-------------------------------------------------------------------------------
class DriverViewSet(BaseViewSet):
    model = Driver

driver_viewset = DriverViewSet(name="drivers")
del driver_viewset.views['delete']


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "is_active"]

    is_driver = forms.BooleanField(initial=True, required=False)
    is_dispatcher = forms.BooleanField(required=False)

    password = forms.CharField(widget=forms.PasswordInput(), required=False)
    confirm_password = forms.CharField(widget=forms.PasswordInput(), required=False)

    def clean(self):
        data = self.cleaned_data

        # new users require passwords
        if not (self.instance or self.instance.pk) and not data.get("password"):
            raise forms.ValidationError("Creating a new user requires a password to be set")

        # if given password but it dosen't match
        if data.get("password") and data.get("password") != data.get("confirm_password"):
            raise forms.ValidationError("Passwords do not match")

        if not (data.get("is_driver", False) or data.get("is_dispatcher", False)):
            raise forms.ValidationError("User must be a driver, dispatcher or both")

        return data


class DriverManipulateMixin(object):
    form_class = UserForm

    def form_valid(self, form):
        self.object = form.save(commit=False)
        if form.cleaned_data.get("password"):
            self.object.set_password(form.cleaned_data["password"])

        # provide a username so Django doesn't choke
        if not self.object.username:
            self.object.username = "%s%s" % (self.object.last_name, random.randint(0, 99))

        self.object.save()

        # update profile
        profile = self.object.profile
        profile.is_driver = form.cleaned_data["is_driver"]
        profile.is_dispatcher = form.cleaned_data["is_dispatcher"]
        profile.save()

        return redirect(self.get_success_url())


@driver_viewset.register("create")
class DriverCreateView(ViewSetMixin, DriverManipulateMixin, CreateView):
    pass


@driver_viewset.register("update")
class DriverUpdateView(ViewSetMixin, DriverManipulateMixin, UpdateView):
    pass


class LocationForm(forms.ModelForm):
    class Meta:
        model = Location

    fieldsets = (
        ("", {
            "fields": ("name", "street", "street2", "city", "state", "postal_code", "county", "country")
        }),
        ("Geolocation", {
            "fields": ("update_location", "latitude", "longitude"),
            "classes": ("collapsed",)
        }),
    )


@location_viewset.register("create")
@location_viewset.register("update")
class LocationCreateView(ViewSetMixin, ModelFormWithInlinesView):
    model = Location
    form_class = LocationForm
    inlines = [Inline(WellSite, template="forms/stacked_inline.html")]


#-------------------------------------------------------------------------------
# Order Views
#-------------------------------------------------------------------------------
class OrderViewSet(BaseViewSet):
    model = Order

order_viewset = OrderViewSet()
del order_viewset.views['delete']


class BaseOrderForm(forms.ModelForm):
    class Meta:
        model = Order

    customer = AutoCompleteField(Company, url="api-customers-search")
    origin = AutoCompleteField(Location, url="api-origins-search")
    destination = AutoCompleteField(Location, url="api-destinations-search")


# Order Create View ------------------------------------------------------------
class OrderCreateForm(BaseOrderForm):
    class Meta:
        model = Order
        fields = ["customer", "commodity", "origin", "destination", "notes"]


@order_viewset.register("create")
class OrderCreateView(ViewSetMixin, CreateView):
    form_class = OrderCreateForm


# Order list/search View --------------------------------------------------------------
@order_viewset.register("list")
class OrderSearchView(SearchMixin, ViewSetMixin, ListView):
    paginate_by = 25

    def perform_search(self, queryset):
        filters = {
            "pending-dispatch": dict(dispatched_at__isnull=True),
            "dispatched": dict(
                dispatched_at__isnull=False,
                driver_accepted_at__isnull=True
            ),
            "in-progress": dict(
                dispatched_at__isnull=False,
                driver_accepted_at__isnull=False,
                order_closed_at__isnull=True
            ),
            "completed": dict(
                dispatched_at__isnull=False,
                driver_accepted_at__isnull=False,
                order_closed_at__isnull=False
            ),
        }
        status = self.request.REQUEST.get("status")
        if status and status in filters.keys():
            return queryset.filter(**filters[status])
        return queryset


# Order update View ------------------------------------------------------------
class OrderUpdateForm(BaseOrderForm):
    class Meta:
        model = Order

    driver = AutoCompleteField(User, url="api-drivers-search")

    fieldsets = (
        ("", {"fields": ["commodity", "customer", "origin", "destination",
            "reroute_destination", "driver", "truck", "trailer",
            "dispatched_at", "driver_accepted_at", "order_closed_at",
            "notes"]}),
        ("Pick Up", {"fields": ["pick_up_completed_at",
            "pick_up_demurrage_minutes", "pick_up_odometer_reading",
            "driver_pick_up_notes", ]}),
        ("Drop Off", {"fields": ["drop_off_completed_at",
            "drop_off_demurrage_minutes", "drop_off_odometer_reading",
            "driver_drop_off_notes", ]}),
    )


@order_viewset.register("update")
class OrderUpdateView(ViewSetMixin, UpdateView):
    form_class = OrderUpdateForm


# Order Dispatch View ----------------------------------------------------------
class OrderDispatchForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["driver"]

    driver = AutoCompleteField(Driver, url="api-drivers-search")


@order_viewset.instance_view("dispatch")
class OrderDispatchView(ViewSetMixin, UpdateView):
    form_class = OrderDispatchForm

    def form_valid(self, form):
        self.object.dispatched_at = timezone.now()
        self.object.save()

        return redirect(self.get_success_url())

    def get_success_url(self):
        return ViewSetMixin.get_success_url(self)


#-------------------------------------------------------------------------------
# Measurement Views
#-------------------------------------------------------------------------------
class OrderMeasurementViewSet(BaseViewSet):
    model = OrderMeasurement

measurement_viewset = OrderMeasurementViewSet()
# del measurement_viewset.views['list']
del measurement_viewset.views['create']
del measurement_viewset.views['update']
del measurement_viewset.views['delete']


#-------------------------------------------------------------------------------
# Company Views
#-------------------------------------------------------------------------------
class CompanyViewSet(BaseViewSet):
    model = Company

company_viewset = CompanyViewSet()
# del measurement_viewset.views['list']
del company_viewset.views['create']
del company_viewset.views['update']
del company_viewset.views['delete']
