"""
WebSocket consumer for 1:1 chat.

Client connects to:  ws://host/ws/chat/<conversation_id>/?token=<access_jwt>

The consumer:
  1. Authenticates via JWTAuthMiddleware (scope['user']).
  2. Verifies the user is a participant in this conversation.
  3. Joins the channels group `chat_<conversation_id>`.
  4. Forwards any message sent via WS to the REST-path's send logic so
     persistence + broadcast stay in one place. For simplicity this consumer
     expects clients to POST to /send/ for sending; it only listens for
     broadcasts pushed by the REST view.

Why not allow sending via WS? REST handles validation, connection checks,
blocking, DB writes — keeping one path avoids duplicate logic. WS is
strictly for live receive here. Clients POST to send, listen on WS.
"""
import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Conversation


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.conversation_id = int(self.scope['url_route']['kwargs']['conversation_id'])
        if not await self._user_is_participant(user, self.conversation_id):
            await self.close(code=4403)
            return

        self.group_name = f'chat_{self.conversation_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connected', 'conversation_id': self.conversation_id})

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Clients are expected to POST messages via REST (/send/).
        # If they send anything here we just ignore it (ping/pong excepted).
        if content.get('type') == 'ping':
            await self.send_json({'type': 'pong'})

    # ── Group event handlers ──────────────────────────────────────────
    async def chat_message(self, event):
        """Called when the REST view broadcasts a new message to this group."""
        await self.send_json({
            'type': 'message',
            'message': event['message'],
        })

    @database_sync_to_async
    def _user_is_participant(self, user, conversation_id):
        try:
            conv = Conversation.objects.get(pk=conversation_id)
        except Conversation.DoesNotExist:
            return False
        return conv.has_participant(user)
