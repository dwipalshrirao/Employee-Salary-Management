import logging

from django.http import Http404, JsonResponse
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotAuthenticated,
    NotFound,
    ParseError,
    PermissionDenied,
    UnsupportedMediaType,
    ValidationError,
)
from rest_framework.response import Response

logger = logging.getLogger("common")


class AppError(Exception):
    status_code = 500
    code = "internal_error"
    message = "Unexpected error."

    def __init__(self, message=None, code=None, details=None, headers=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or {}
        self.headers = headers or {}


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "Not found."


class ConflictError(AppError):
    status_code = 409
    code = "conflict"
    message = "Conflict."


class StaleCountError(AppError):
    status_code = 409
    code = "stale_preview"
    message = "Preview is stale."


class ResultTooLargeError(AppError):
    status_code = 422
    code = "result_too_large"
    message = "Result is too large."


class RateLimitedError(AppError):
    status_code = 429
    code = "rate_limited"
    message = "Too many requests."


def _drf_response(code, message, details, response_status):
    return Response(
        {
            "error": {
                "code": code,
                "message": message,
                "details": details,
            }
        },
        status=response_status,
    )


def not_found():
    return _drf_response("not_found", "Not found.", {}, 404)


def internal_error():
    return _drf_response("internal_error", "Internal server error.", {}, 500)


def not_found_response(request, exception=None):
    return JsonResponse(
        {
            "error": {
                "code": "not_found",
                "message": "Not found.",
                "details": {},
            }
        },
        status=404,
        content_type="application/json",
    )


def _request_details(request):
    request_id = getattr(request, "request_id", None)
    return {"request_id": request_id} if request_id else {}


def internal_error_response(request, exception=None):
    return JsonResponse(
        {
            "error": {
                "code": "internal_error",
                "message": "Internal server error.",
                "details": _request_details(request),
            }
        },
        status=500,
        content_type="application/json",
    )


def handler(exc, context):
    if isinstance(exc, AppError):
        response = _drf_response(
            exc.code,
            exc.message,
            exc.details,
            exc.status_code,
        )
        for header, value in exc.headers.items():
            response[header] = value
        return response

    if isinstance(exc, Http404 | NotFound):
        return not_found()

    if isinstance(exc, ValidationError):
        return _drf_response("validation_error", "Invalid input.", exc.detail, 422)

    if isinstance(exc, ParseError):
        return _drf_response(
            "validation_error",
            "Invalid input.",
            {"non_field_errors": ["Malformed JSON body."]},
            422,
        )

    if isinstance(exc, UnsupportedMediaType):
        return _drf_response("validation_error", "Unsupported media type.", {}, 422)

    if isinstance(exc, NotAuthenticated):
        return _drf_response("unauthorized", "Authentication required.", {}, 401)

    if isinstance(exc, AuthenticationFailed):
        return _drf_response("unauthorized", str(exc.detail), {}, 401)

    if isinstance(exc, PermissionDenied) and str(exc).startswith("CSRF Failed"):
        return _drf_response("csrf_failed", "CSRF failed.", {}, 403)

    request = context.get("request")
    request_id = getattr(request, "request_id", None)
    logger.error(
        "unhandled_exception",
        exc_info=exc,
        extra={"request_id": request_id},
    )
    return _drf_response(
        "internal_error",
        "Internal server error.",
        _request_details(request),
        500,
    )
