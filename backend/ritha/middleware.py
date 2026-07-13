"""
Request / response logging middleware.
Logs method, path, status code, duration, and user for every API request.
Sensitive paths (login, password) have their bodies redacted.
"""

import logging
import time

logger = logging.getLogger("ritha.requests")


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration = round((time.monotonic() - start) * 1000, 1)

        # Log the user id, not the email — avoid PII in request logs / Sentry breadcrumbs.
        user = request.user.id if hasattr(request, "user") and request.user.is_authenticated else "anon"

        logger.info(
            "%s %s %s %sms user=%s",
            request.method,
            request.path,
            response.status_code,
            duration,
            user,
        )

        return response
