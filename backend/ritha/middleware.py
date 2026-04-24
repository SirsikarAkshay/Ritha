"""
Request / response logging middleware.
Logs method, path, status code, duration, and user for every API request.
Sensitive paths (login, password) have their bodies redacted.
"""
import time
import logging
import json

logger = logging.getLogger('ritha.requests')

# Paths whose request bodies should never appear in logs
_REDACT_PATHS = {'/api/auth/login/', '/api/auth/register/', '/api/auth/me/password/'}


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start    = time.monotonic()
        response = self.get_response(request)
        duration = round((time.monotonic() - start) * 1000, 1)

        user = (
            request.user.email
            if hasattr(request, 'user') and request.user.is_authenticated
            else 'anon'
        )

        logger.info(
            '%s %s %s %sms user=%s',
            request.method,
            request.path,
            response.status_code,
            duration,
            user,
        )

        return response
