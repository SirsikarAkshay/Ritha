"""
Custom DRF exception handler.

All API errors return a consistent JSON envelope:
  {
    "error": {
      "code":    "validation_error",
      "message": "Human-readable summary — safe to show in the UI",
      "detail":  <original DRF detail — dict, list, or string>
    }
  }
"""
from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    ValidationError, AuthenticationFailed, NotAuthenticated,
    PermissionDenied, NotFound, MethodNotAllowed, Throttled,
)
from rest_framework.response import Response
from django.http import Http404
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
import logging

logger = logging.getLogger('arokah.api')

_CODE_MAP = {
    ValidationError:      'validation_error',
    AuthenticationFailed: 'authentication_failed',
    NotAuthenticated:     'not_authenticated',
    PermissionDenied:     'permission_denied',
    NotFound:             'not_found',
    MethodNotAllowed:     'method_not_allowed',
    Throttled:            'rate_limit_exceeded',
}


def _flatten_detail(detail) -> str:
    """
    Convert DRF's nested error structure into one readable sentence.
    Handles dicts, lists, ErrorDetail objects, and strings.
    """
    if isinstance(detail, str):
        return detail

    if isinstance(detail, list):
        messages = []
        for item in detail:
            messages.append(_flatten_detail(item))
        return ' '.join(m for m in messages if m)

    if isinstance(detail, dict):
        messages = []
        for field, value in detail.items():
            flat = _flatten_detail(value)
            if field == 'non_field_errors':
                messages.append(flat)
            else:
                # Make field names readable: "email" → "Email"
                readable_field = field.replace('_', ' ').capitalize()
                messages.append(f'{readable_field}: {flat}')
        return ' '.join(m for m in messages if m)

    # ErrorDetail or other — convert to string
    return str(detail)


def _human_message(exc, detail) -> str:
    """Return a concise, UI-safe error message."""
    if isinstance(exc, ValidationError):
        # Prefer the flattened detail for validation errors
        flat = _flatten_detail(detail)
        if flat and flat != '{}':
            # Capitalise and ensure period
            msg = flat.strip()
            return msg if msg.endswith('.') else msg + '.'
        return 'One or more fields are invalid.'

    if isinstance(exc, AuthenticationFailed):
        return str(exc.detail) if hasattr(exc, 'detail') else 'Invalid credentials.'

    if isinstance(exc, NotAuthenticated):
        return 'You must be logged in to access this resource.'

    if isinstance(exc, PermissionDenied):
        return 'You do not have permission to perform this action.'

    if isinstance(exc, NotFound):
        return 'The requested resource was not found.'

    if isinstance(exc, MethodNotAllowed):
        return f'Method not allowed.'

    if isinstance(exc, Throttled):
        wait = getattr(exc, 'wait', None)
        return f'Too many requests. Please wait {int(wait)} seconds.' if wait else 'Too many requests.'

    return 'An unexpected error occurred. Please try again.'


def custom_exception_handler(exc, context):
    # Convert Django exceptions to DRF equivalents
    if isinstance(exc, Http404):
        exc = NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = PermissionDenied()

    response = exception_handler(exc, context)

    if response is not None:
        original_detail = response.data
        code            = _CODE_MAP.get(type(exc), 'error')
        message         = _human_message(exc, original_detail)

        # For validation errors, also provide structured field errors
        structured_detail = original_detail
        if isinstance(exc, ValidationError) and isinstance(original_detail, dict):
            # Flatten each field's error list to a single string
            structured_detail = {
                field: (_flatten_detail(msgs) if not isinstance(msgs, str) else msgs)
                for field, msgs in original_detail.items()
            }

        response.data = {
            'error': {
                'code':    code,
                'message': message,
                'detail':  structured_detail,
            }
        }

        # Log 5xx responses
        if response.status_code >= 500:
            logger.error(
                'API error %s on %s %s: %s',
                response.status_code,
                context['request'].method,
                context['request'].path,
                original_detail,
            )

    return response
