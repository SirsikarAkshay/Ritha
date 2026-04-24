"""
JWT authentication middleware for Django Channels WebSocket connections.

Usage on the client side:
    ws://host/ws/chat/<conversation_id>/?token=<access_jwt>

The middleware reads the `token` query param, validates it as a SimpleJWT
access token, resolves the user, and attaches them to `scope['user']`.
If the token is missing or invalid, `scope['user']` is AnonymousUser and
the consumer should reject the connection.
"""
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


@database_sync_to_async
def _get_user(user_id):
    try:
        return User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        query_string = scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token = (params.get('token') or [None])[0]

        if token:
            try:
                validated = AccessToken(token)
                scope['user'] = await _get_user(validated['user_id'])
            except (InvalidToken, TokenError, KeyError):
                scope['user'] = AnonymousUser()
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)


def JWTAuthMiddlewareStack(inner):
    return JWTAuthMiddleware(inner)
