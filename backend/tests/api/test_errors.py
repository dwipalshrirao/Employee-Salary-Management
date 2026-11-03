import logging

import pytest
from rest_framework.exceptions import NotFound, UnsupportedMediaType, ValidationError
from rest_framework.views import APIView

import common.errors as errors
from common.errors import NotFoundError, handler


def _exception_context():
    return {"view": APIView(), "args": [], "kwargs": {}}


def test_not_found_error_uses_standard_error_shape():
    response = handler(NotFoundError(), _exception_context())

    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"


def test_drf_validation_error_is_422_not_400():
    validation_error = ValidationError({"email": ["A valid email is required."]})

    response = handler(validation_error, _exception_context())

    assert response.status_code == 422
    assert response.data["error"]["code"] == "validation_error"


def test_unknown_url_returns_standard_error_shape(client):
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_drf_not_found_uses_standard_error_shape():
    response = handler(NotFound(), _exception_context())

    assert response.status_code == 404
    assert response.data["error"]["code"] == "not_found"


@pytest.mark.parametrize(
    ("class_name", "status_code", "code"),
    [
        ("ConflictError", 409, "conflict"),
        ("StaleCountError", 409, "stale_preview"),
        ("ResultTooLargeError", 422, "result_too_large"),
        ("RateLimitedError", 429, "rate_limited"),
    ],
)
def test_app_error_subclasses_use_standard_error_shape(class_name, status_code, code):
    error_class = getattr(errors, class_name, None)
    assert error_class is not None, f"{class_name} is not defined"

    response = handler(error_class(), _exception_context())

    assert response.status_code == status_code
    assert response.data["error"]["code"] == code


def test_unsupported_media_type_is_422_validation_error():
    response = handler(UnsupportedMediaType("application/xml"), _exception_context())

    assert response.status_code == 422
    assert response.data["error"]["code"] == "validation_error"


def test_internal_error_returns_request_id_without_leaking_details():
    class _Request:
        request_id = "req-1"

    context = _exception_context()
    context["request"] = _Request()

    response = handler(RuntimeError("secret internal details"), context)

    assert response.status_code == 500
    assert response.data["error"] == {
        "code": "internal_error",
        "message": "Internal server error.",
        "details": {"request_id": "req-1"},
    }


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def test_internal_error_logs_traceback_with_request_id():
    class _Request:
        request_id = "req-1"

    context = _exception_context()
    context["request"] = _Request()
    logger = logging.getLogger("common")
    handler_instance = _ListHandler()
    logger.addHandler(handler_instance)

    try:
        try:
            raise RuntimeError("secret internal details")
        except RuntimeError as exc:
            response = handler(exc, context)
    finally:
        logger.removeHandler(handler_instance)

    assert response.status_code == 500
    record = handler_instance.records[0]
    assert record.getMessage() == "unhandled_exception"
    assert record.request_id == "req-1"
    assert record.exc_info is not None
    formatted = logging.Formatter().formatException(record.exc_info)
    assert "Traceback" in formatted
    assert "RuntimeError: secret internal details" in formatted
