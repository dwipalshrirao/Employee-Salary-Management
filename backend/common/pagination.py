"""Shared pagination helpers for list selectors."""


def paginate_queryset(queryset, page, page_size):
    """Return one stable page and the total count using two queries."""
    total = queryset.count()
    offset = (page - 1) * page_size
    items = list(queryset[offset : offset + page_size])
    return items, total
