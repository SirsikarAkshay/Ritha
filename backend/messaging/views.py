"""
REST endpoints for messaging.

- Conversations are auto-created the first time one user messages another.
- Both REST send and WebSocket send persist to DB and broadcast via channels,
  so clients with an open WS see messages live, and REST-only clients still work.
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q

logger = logging.getLogger(__name__)
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from social.models import BlockedUser, Connection
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer


def _broadcast_message(conversation_id: int, message: Message):
    """Push a new message to the per-conversation channels group.

    Broadcast failures (e.g. Redis unreachable) must NOT fail the request —
    the message is already persisted and will appear on the next history fetch.
    """
    try:
        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            f'chat_{conversation_id}',
            {
                'type': 'chat.message',
                'message': {
                    'id': message.id,
                    'conversation': conversation_id,
                    'sender': message.sender_id,
                    'body': message.body,
                    'created_at': message.created_at.isoformat(),
                },
            },
        )
    except Exception as e:
        logger.warning('Chat broadcast failed for conversation %s: %s', conversation_id, e)


class ConversationListView(ListAPIView):
    """GET /api/messages/conversations/ — list my conversations."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = ConversationSerializer

    def get_queryset(self):
        me = self.request.user
        return Conversation.objects.filter(
            Q(user_a=me) | Q(user_b=me)
        ).order_by('-updated_at')


class ConversationOpenView(APIView):
    """POST /api/messages/conversations/open/  body: { user_id }
    Get or create the 1:1 conversation with `user_id`. Users must be connected."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        target_id = request.data.get('user_id')
        if not target_id:
            return Response(
                {'error': {'code': 'missing_fields', 'message': '`user_id` is required.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            target = User.objects.get(id=target_id, is_active=True)
        except User.DoesNotExist:
            return Response(
                {'error': {'code': 'not_found', 'message': 'User not found.'}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if target.pk == request.user.pk:
            return Response(
                {'error': {'code': 'invalid', 'message': 'Cannot message yourself.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if BlockedUser.is_blocked_either_way(request.user, target):
            return Response(
                {'error': {'code': 'blocked', 'message': 'You cannot message this user.'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        if not Connection.are_connected(request.user, target):
            return Response(
                {'error': {'code': 'not_connected',
                           'message': 'You can only message users you are connected with.'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        conv, _ = Conversation.get_or_create_between(request.user, target)
        serializer = ConversationSerializer(conv, context={'request': request})
        return Response(serializer.data)


class MessageListView(ListAPIView):
    """GET /api/messages/conversations/<id>/messages/?before_id=N — message history."""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = MessageSerializer
    pagination_class   = None  # Simple before_id pagination below

    def get_queryset(self):
        conv_id = self.kwargs['pk']
        me = self.request.user
        try:
            conv = Conversation.objects.get(pk=conv_id)
        except Conversation.DoesNotExist:
            return Message.objects.none()
        if not conv.has_participant(me):
            return Message.objects.none()

        qs = conv.messages.all()
        before_id = self.request.query_params.get('before_id')
        if before_id:
            qs = qs.filter(id__lt=before_id)
        return qs.order_by('-created_at')[:50]

    def list(self, request, *args, **kwargs):
        # Return in chronological order even though we fetch desc for the limit
        qs = list(self.get_queryset())
        qs.reverse()
        return Response(MessageSerializer(qs, many=True).data)


class SendMessageView(APIView):
    """POST /api/messages/conversations/<id>/send/  body: { body }"""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        body = (request.data.get('body') or '').strip()
        if not body:
            return Response(
                {'error': {'code': 'empty', 'message': 'Message body cannot be empty.'}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(body) > 4000:
            return Response(
                {'error': {'code': 'too_long', 'message': 'Message too long (max 4000 characters).'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            conv = Conversation.objects.get(pk=pk)
        except Conversation.DoesNotExist:
            return Response(
                {'error': {'code': 'not_found', 'message': 'Conversation not found.'}},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not conv.has_participant(request.user):
            return Response(
                {'error': {'code': 'forbidden', 'message': 'Not a participant of this conversation.'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Re-verify connection status in case it changed
        other = conv.other_user(request.user)
        if BlockedUser.is_blocked_either_way(request.user, other):
            return Response(
                {'error': {'code': 'blocked', 'message': 'You cannot message this user.'}},
                status=status.HTTP_403_FORBIDDEN,
            )
        if not Connection.are_connected(request.user, other):
            return Response(
                {'error': {'code': 'not_connected',
                           'message': 'You are no longer connected with this user.'}},
                status=status.HTTP_403_FORBIDDEN,
            )

        msg = Message.objects.create(conversation=conv, sender=request.user, body=body)
        conv.updated_at = timezone.now()
        conv.save(update_fields=['updated_at'])

        _broadcast_message(conv.id, msg)
        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class MarkReadView(APIView):
    """POST /api/messages/conversations/<id>/mark_read/ — mark all as read now."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            conv = Conversation.objects.get(pk=pk)
        except Conversation.DoesNotExist:
            return Response(
                {'error': {'code': 'not_found', 'message': 'Conversation not found.'}},
                status=status.HTTP_404_NOT_FOUND,
            )
        if not conv.has_participant(request.user):
            return Response(
                {'error': {'code': 'forbidden', 'message': 'Not a participant.'}},
                status=status.HTTP_403_FORBIDDEN,
            )
        now = timezone.now()
        if request.user.pk == conv.user_a_id:
            conv.user_a_read_at = now
            conv.save(update_fields=['user_a_read_at'])
        else:
            conv.user_b_read_at = now
            conv.save(update_fields=['user_b_read_at'])
        return Response({'status': 'ok'})
