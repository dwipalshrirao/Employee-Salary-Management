import json
import logging

from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory

import common.middleware as middleware_module
from common.middleware import RequestMonitoringMiddleware


def _log_record(**fields):
    record = logging.LogRecord(
        "common", logging.INFO, __file__, 1, "request_completed", (), None
    )
    for key, value in fields.items():
        setattr(record, key, value)
    return record


def test_structured_formatter_emits_request_fields():
    formatter_class = getattr(middleware_module, "StructuredFormatter", None)
    assert formatter_class is not None, "StructuredFormatter is not defined"

    payload = json.loads(
        formatter_class().format(
            _log_record(
                request_id="req-1",
                method="GET",
                path="/api/health",
                status=200,
                duration_ms=3,
                user_id=None,
            )
        )
    )

    assert payload["request_id"] == "req-1"
    assert payload["method"] == "GET"
    assert payload["path"] == "/api/health"
    assert payload["status"] == 200
    assert payload["duration_ms"] == 3
    assert payload["user_id"] is None
    assert payload["message"] == "request_completed"


def test_logging_config_uses_structured_formatter():
    assert (
        settings.LOGGING["formatters"]["structured"].get("()")
        == "common.middleware.StructuredFormatter"
    )


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def test_middleware_log_does_not_include_request_body():
    body = "super-secret-request-body"
    request = RequestFactory().post(
        "/api/employees", data=body, content_type="application/json"
    )
    middleware = RequestMonitoringMiddleware(lambda _request: HttpResponse())
    logger = logging.getLogger("common")
    handler = _ListHandler()
    logger.addHandler(handler)

    try:
        middleware(request)
    finally:
        logger.removeHandler(handler)

    record = handler.records[-1]
    assert record.request_id
    assert record.method == "POST"
    assert record.path == "/api/employees"
    assert body not in record.getMessage()


def test_middleware_adds_only_operational_headers():
    response = HttpResponse()
    request = RequestFactory().get("/api/health")
    middleware = RequestMonitoringMiddleware(lambda _request: response)

    result = middleware(request)

    assert result["X-Request-ID"]
    assert result["Cache-Control"] == "no-store"
    assert "X-Content-Type-Options" not in result
    assert "X-Frame-Options" not in result
    assert "Referrer-Policy" not in result
