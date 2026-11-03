import json
import logging
import time
import uuid

logger = logging.getLogger("common")

_REQUEST_LOG_FIELDS = (
    "request_id",
    "method",
    "path",
    "status",
    "duration_ms",
    "user_id",
)


class StructuredFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _REQUEST_LOG_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class RequestMonitoringMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = request.META.get("HTTP_X_REQUEST_ID", uuid.uuid4().hex)
        started_at = time.perf_counter()
        response = self.get_response(request)
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        user = getattr(request, "user", None)
        user_id = getattr(user, "id", None)
        logger.info(
            "request_completed",
            extra={
                "request_id": request.request_id,
                "method": request.method,
                "path": request.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "user_id": user_id,
            },
        )
        response["X-Request-ID"] = request.request_id
        # Lookups intentionally sets a private cache header; keep it instead of
        # forcing no-store for every API response.
        if request.path.startswith("/api/") and "Cache-Control" not in response:
            response["Cache-Control"] = "no-store"
        return response
