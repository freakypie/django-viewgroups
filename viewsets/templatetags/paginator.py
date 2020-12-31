from django import template
from django.conf import settings
from django.core.paginator import Paginator, InvalidPage


register = template.Library()


@register.simple_tag
def paginate(request, queryset, per_page=25, page_var="page"):
    page = request.REQUEST.get(page_var, 1)
    try:
        return Paginator(queryset, per_page).page(page)
    except InvalidPage:
        pass
    return Paginator(queryset, per_page).page(1)


@register.filter
def pages(page, span=5):
    paginator = page.paginator

    pages = []
    if page.has_other_pages():

        max = span * 2 + 1
        lower_span = page.number - span
        if max > paginator.num_pages:
            lower_span -= max - paginator.num_pages
            max = paginator.num_pages

        if lower_span <= 1:
            lower_span = 1
        else:
            pages += [None]

        for idx in range(max):
            try:
                pages += [paginator.page(lower_span + idx)]
            except:
                pass

        if lower_span + max <= paginator.num_pages:
            pages += [None]

    return pages
