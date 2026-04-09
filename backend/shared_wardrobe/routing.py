from django.urls import re_path

from .consumers import SharedWardrobeConsumer

websocket_urlpatterns = [
    re_path(r'^ws/shared-wardrobe/(?P<wardrobe_id>\d+)/$', SharedWardrobeConsumer.as_asgi()),
]
