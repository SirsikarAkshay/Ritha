"""
WebSocket consumer for shared wardrobes.

Client connects to:  ws://host/ws/shared-wardrobe/<wardrobe_id>/?token=<access_jwt>

Receives live updates whenever any member adds/removes an item, another
member is added/removed, or the wardrobe is deleted. Send path is REST-only
(same reasoning as chat).
"""
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import SharedWardrobe


class SharedWardrobeConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.wardrobe_id = int(self.scope['url_route']['kwargs']['wardrobe_id'])
        if not await self._is_member(user, self.wardrobe_id):
            await self.close(code=4403)
            return

        self.group_name = f'sharedwardrobe_{self.wardrobe_id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({'type': 'connected', 'wardrobe_id': self.wardrobe_id})

    async def disconnect(self, code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        if content.get('type') == 'ping':
            await self.send_json({'type': 'pong'})

    # ── Group event handler ───────────────────────────────────────────
    async def wardrobe_event(self, event):
        """Forward any wardrobe mutation to the client verbatim."""
        await self.send_json({
            'type':       event['event_type'],
            'payload':    event['payload'],
        })

    @database_sync_to_async
    def _is_member(self, user, wardrobe_id):
        try:
            wardrobe = SharedWardrobe.objects.get(pk=wardrobe_id)
        except SharedWardrobe.DoesNotExist:
            return False
        return wardrobe.is_member(user)
