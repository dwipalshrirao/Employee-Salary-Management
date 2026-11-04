import pytest
from django.urls import URLPattern, URLResolver

from config.urls import urlpatterns

pytestmark = pytest.mark.django_db


def _walk_routes(patterns, prefix=""):
    for pattern in patterns:
        route = f"{prefix}{pattern.pattern}"
        if isinstance(pattern, URLResolver):
            yield from _walk_routes(pattern.url_patterns, route)
        elif isinstance(pattern, URLPattern) and route.startswith("api/"):
            yield route


METHODS = {
    "api/auth/me": ("get",),
    "api/auth/logout": ("post",),
    "api/lookups": ("get",),
    "api/employees": ("get", "post"),
    "api/employees/<int:pk>": ("get", "patch"),
    "api/employees/<int:pk>/direct-reports": ("get",),
    "api/employees/<int:pk>/history": ("get",),
    "api/employees/<int:pk>/deactivate": ("post",),
    "api/employees/<int:pk>/reactivate": ("post",),
    "api/salary-history": ("get",),
    "api/bulk-updates/preview": ("post",),
    "api/bulk-updates/apply": ("post",),
    "api/analytics/summary": ("get",),
    "api/analytics/breakdown": ("get",),
    "api/analytics/distribution": ("get",),
    "api/analytics/outliers": ("get",),
    "api/analytics/team/<int:manager_id>": ("get",),
}


def _sample_path(route):
    return route.replace("<int:pk>", "1").replace("<int:manager_id>", "1")


def _session_required_cases():
    exempt = {"api/health", "api/auth/login"}
    # Swagger UI and its generated schema are developer tooling rather than
    # business API routes, so they stay public for local exploration.
    tooling = {"api/docs/", "api/docs/schema/"}
    for route in _walk_routes(urlpatterns):
        if route in exempt or route in tooling:
            continue
        path = _sample_path(route)
        assert "<" not in path, f"unresolved route parameter in {route}"
        for method in METHODS[route]:
            yield method, f"/{path}"


@pytest.mark.parametrize(("method", "path"), list(_session_required_cases()))
def test_every_business_route_except_health_and_login_requires_a_session(
    client, method, path
):
    response = getattr(client, method)(path)

    assert response.status_code == 401
