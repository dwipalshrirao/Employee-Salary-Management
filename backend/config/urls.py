from django.urls import path
from drf_spectacular.views import SpectacularAPIView

from common.errors import internal_error_response, not_found_response
from common.views import ApiDocsView, HealthView


def _not_found(request, exception=None):
    return not_found_response(request, exception)


def _internal_error(request, exception=None):
    return internal_error_response(request, exception)


handler404 = _not_found
handler500 = _internal_error


urlpatterns = [
    path("api/health", HealthView.as_view()),
    path("api/docs/schema/", SpectacularAPIView.as_view(), name="docs-schema"),
    path("api/docs/", ApiDocsView.as_view(), name="swagger-ui"),
]
