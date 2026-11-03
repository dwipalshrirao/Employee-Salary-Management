"""Read-only queries for reference data used by the UI."""

from catalog.models import Country, CurrencyRate, Department, JobTitle


def get_lookups():
    """Return all lookup querysets in a stable order for predictable clients."""
    return {
        "countries": Country.objects.select_related("currency_code").order_by("code"),
        "departments": Department.objects.order_by("name"),
        "job_titles": JobTitle.objects.order_by("name"),
        "currency_rates": CurrencyRate.objects.order_by("currency_code"),
    }
