"""
ASGI config for Arokah.

HTTP traffic goes through Django's standard ASGI handler.
WebSocket traffic (ws://.../ws/...) is routed via Channels to per-app consumers.
"""
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arokah.settings')

# Set up Django BEFORE importing anything that touches models/settings.
import django
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

from arokah.ws_auth import JWTAuthMiddlewareStack

# Collect WS URL patterns from each app that ships a routing.py
from messaging.routing import websocket_urlpatterns as messaging_ws
from shared_wardrobe.routing import websocket_urlpatterns as shared_wardrobe_ws

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        JWTAuthMiddlewareStack(
            URLRouter(messaging_ws + shared_wardrobe_ws)
        )
    ),
})
