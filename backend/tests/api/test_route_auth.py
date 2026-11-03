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


def _session_required_cases():
    exempt = {"api/health", "api/auth/login"}
    # Swagger UI and its generated schema are developer tooling rather than
    # business API routes, so they stay public for local exploration.
    tooling = {"api/docs/", "api/docs/schema/"}
    for route in _walk_routes(urlpatterns):
        if route in exempt or route in tooling or "<" in route:
            continue
        method = "post" if route == "api/auth/logout" else "get"
        yield method, f"/{route}"


@pytest.mark.parametrize(("method", "path"), list(_session_required_cases()))
def test_every_business_route_except_health_and_login_requires_a_session(
    client, method, path
):
    response = getattr(client, method)(path)

    assert response.status_code == 401
