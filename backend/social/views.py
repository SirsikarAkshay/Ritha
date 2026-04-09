"""
REST endpoints for the social graph:
  /api/social/me/profile/            GET, PATCH
  /api/social/me/profile/handle/     POST            (change handle, 30-day cooldown)
  /api/social/users/search/          GET  ?handle=<exact>

  /api/social/connections/           GET             (list — filter by ?status=)
  /api/social/connections/request/   POST            {handle}
  /api/social/connections/<id>/accept/   POST
  /api/social/connections/<id>/reject/   POST
  /api/social/connections/<id>/      DELETE          (cancel pending OR remove accepted)

  /api/social/blocks/                GET             (list my blocks)
  /api/social/blocks/                POST            {handle}
  /api/social/blocks/<id>/           DELETE
"""
from django.contrib.auth import get_user_model
from django.db import IntegrityError, models
from django.shortcuts import get_object_or_404
from django.utils import timezone as dj_timezone
from rest_framework import permissions, status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BlockedUser, Connection, ConnectionStatus, Profile, ProfileVisibility
from .serializers import (
    BlockedUserSerializer,
    ConnectionSerializer,
    MyProfileSerializer,
    PublicUserSerializer,
    UpdateHandleSerializer,
)

User = get_user_model()


def _err(code: str, message: str, *, status_code=status.HTTP_400_BAD_REQUEST, **extra):
    return Response({'error': {'code': code, 'message': message, **extra}}, status=status_code)


def _get_or_create_profile(user) -> Profile:
    """Lazy-create for users that predate the social app or have a missing profile."""
    profile, _ = Profile.objects.get_or_create(
        user=user,
        defaults={'handle': f'user{user.pk}', 'display_name': user.first_name or ''},
    )
    return profile


# ── Profile ────────────────────────────────────────────────────────────────

class MyProfileView(RetrieveUpdateAPIView):
    """GET/PATCH /api/social/me/profile/"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = MyProfileSerializer
    http_method_names  = ['get', 'patch', 'head', 'options']

    def get_object(self):
        return _get_or_create_profile(self.request.user)


class UpdateHandleView(APIView):
    """POST /api/social/me/profile/handle/  body: { handle }"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    def post(self, request):
        profile = _get_or_create_profile(request.user)
        serializer = UpdateHandleSerializer(
            data=request.data,
            context={'profile': profile},
        )
        if not serializer.is_valid():
            first_error = next(iter(serializer.errors.values()))
            message = first_error[0] if isinstance(first_error, list) else str(first_error)
            return _err('invalid_handle', message)

        profile.handle            = serializer.validated_data['handle']
        profile.handle_changed_at = dj_timezone.now()
        profile.save(update_fields=['handle', 'handle_changed_at', 'updated_at'])
        return Response(MyProfileSerializer(profile).data)


# ── User search ────────────────────────────────────────────────────────────

class UserSearchView(APIView):
    """GET /api/social/users/search/?handle=<exact>"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    def get(self, request):
        handle = request.query_params.get('handle', '').strip().lower()
        if not handle:
            return _err('missing_query', 'Provide a `handle` query parameter.')

        try:
            profile = Profile.objects.select_related('user').get(handle=handle)
        except Profile.DoesNotExist:
            return Response({'found': False, 'user': None})

        target = profile.user

        if target.pk == request.user.pk:
            return Response({
                'found': True,
                'user': PublicUserSerializer(target, context={'viewer': request.user}).data,
                'is_self': True,
            })

        if BlockedUser.is_blocked_either_way(request.user, target):
            # Pretend the user doesn't exist (don't leak that a block is in place)
            return Response({'found': False, 'user': None})

        # Private profiles aren't in this v1 — both public and connections_only are searchable.

        payload = PublicUserSerializer(target, context={'viewer': request.user}).data

        connection = Connection.between(request.user, target)
        if connection:
            payload['connection'] = {
                'id':        connection.pk,
                'status':    connection.status,
                'direction': 'outgoing' if connection.from_user_id == request.user.pk else 'incoming',
            }
        else:
            payload['connection'] = None

        return Response({'found': True, 'user': payload, 'is_self': False})


# ── Connections ───────────────────────────────────────────────────────────

class ConnectionListView(APIView):
    """
    GET /api/social/connections/?status=accepted|pending|rejected
    Returns connections involving the current user, with `other_user` inlined.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    def get(self, request):
        user       = request.user
        status_q   = request.query_params.get('status', '').strip().lower()
        qs = Connection.objects.filter(
            # Either direction involving me
            models.Q(from_user=user) | models.Q(to_user=user)
        ).select_related('from_user', 'to_user').order_by('-updated_at')

        if status_q:
            if status_q not in ConnectionStatus.values:
                return _err('invalid_status', f'status must be one of {list(ConnectionStatus.values)}.')
            qs = qs.filter(status=status_q)

        data = ConnectionSerializer(qs, many=True, context={'viewer': user}).data
        return Response({'results': data, 'count': len(data)})


class ConnectionRequestView(APIView):
    """POST /api/social/connections/request/  body: { handle }"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    def post(self, request):
        handle = (request.data.get('handle') or '').strip().lower()
        if not handle:
            return _err('missing_fields', '`handle` is required.')

        try:
            target_profile = Profile.objects.select_related('user').get(handle=handle)
        except Profile.DoesNotExist:
            return _err('not_found', 'No user with that handle.', status_code=status.HTTP_404_NOT_FOUND)

        target = target_profile.user
        if target.pk == request.user.pk:
            return _err('self_request', 'You cannot send a connection request to yourself.')

        if BlockedUser.is_blocked_either_way(request.user, target):
            return _err(
                'blocked',
                'You cannot send a connection request to this user.',
                status_code=status.HTTP_403_FORBIDDEN,
            )

        existing = Connection.between(request.user, target)
        if existing:
            if existing.status == ConnectionStatus.ACCEPTED:
                return _err('already_connected', 'You are already connected with this user.')
            if existing.status == ConnectionStatus.PENDING:
                if existing.from_user_id == request.user.pk:
                    return _err('already_requested', 'You already sent a request to this user.')
                # They previously requested you — auto-accept? No: return a clear signal.
                return _err(
                    'incoming_pending',
                    'This user has already sent you a connection request. Accept it instead.',
                    connection_id=existing.pk,
                )
            # Rejected — allow a new request by reusing the row
            if existing.status == ConnectionStatus.REJECTED:
                existing.from_user = request.user
                existing.to_user   = target
                existing.status    = ConnectionStatus.PENDING
                existing.save(update_fields=['from_user', 'to_user', 'status', 'updated_at'])
                return Response(
                    ConnectionSerializer(existing, context={'viewer': request.user}).data,
                    status=status.HTTP_201_CREATED,
                )

        try:
            conn = Connection.objects.create(
                from_user=request.user,
                to_user=target,
                status=ConnectionStatus.PENDING,
            )
        except IntegrityError:
            return _err('race_condition', 'A connection request already exists. Please refresh.')

        return Response(
            ConnectionSerializer(conn, context={'viewer': request.user}).data,
            status=status.HTTP_201_CREATED,
        )


class ConnectionAcceptView(APIView):
    """POST /api/social/connections/<id>/accept/"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    def post(self, request, pk):
        conn = get_object_or_404(Connection, pk=pk)
        if conn.to_user_id != request.user.pk:
            return _err(
                'not_allowed',
                'Only the recipient of a request can accept it.',
                status_code=status.HTTP_403_FORBIDDEN,
            )
        if conn.status != ConnectionStatus.PENDING:
            return _err('not_pending', f'Cannot accept a {conn.status} request.')
        conn.status = ConnectionStatus.ACCEPTED
        conn.save(update_fields=['status', 'updated_at'])
        return Response(ConnectionSerializer(conn, context={'viewer': request.user}).data)


class ConnectionRejectView(APIView):
    """POST /api/social/connections/<id>/reject/"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    def post(self, request, pk):
        conn = get_object_or_404(Connection, pk=pk)
        if conn.to_user_id != request.user.pk:
            return _err(
                'not_allowed',
                'Only the recipient of a request can reject it.',
                status_code=status.HTTP_403_FORBIDDEN,
            )
        if conn.status != ConnectionStatus.PENDING:
            return _err('not_pending', f'Cannot reject a {conn.status} request.')
        conn.status = ConnectionStatus.REJECTED
        conn.save(update_fields=['status', 'updated_at'])
        return Response(ConnectionSerializer(conn, context={'viewer': request.user}).data)


class ConnectionDeleteView(APIView):
    """
    DELETE /api/social/connections/<id>/
    Works for:
      - canceling a pending outgoing request (you are from_user)
      - removing an accepted connection from either side
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    def delete(self, request, pk):
        conn = get_object_or_404(Connection, pk=pk)
        if request.user.pk not in (conn.from_user_id, conn.to_user_id):
            return _err(
                'not_allowed',
                'You are not part of this connection.',
                status_code=status.HTTP_403_FORBIDDEN,
            )
        conn.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ── Blocks ────────────────────────────────────────────────────────────────

class BlockListView(APIView):
    """GET /api/social/blocks/  — POST /api/social/blocks/ body: { handle }"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    def get(self, request):
        blocks = BlockedUser.objects.filter(blocker=request.user).select_related('blocked').order_by('-created_at')
        data = BlockedUserSerializer(blocks, many=True, context={'viewer': request.user}).data
        return Response({'results': data, 'count': len(data)})

    def post(self, request):
        handle = (request.data.get('handle') or '').strip().lower()
        if not handle:
            return _err('missing_fields', '`handle` is required.')
        try:
            target = Profile.objects.select_related('user').get(handle=handle).user
        except Profile.DoesNotExist:
            return _err('not_found', 'No user with that handle.', status_code=status.HTTP_404_NOT_FOUND)

        if target.pk == request.user.pk:
            return _err('self_block', 'You cannot block yourself.')

        # Remove any existing connection between the two users — blocks cut the relationship
        Connection.objects.filter(
            models.Q(from_user=request.user, to_user=target)
            | models.Q(from_user=target, to_user=request.user)
        ).delete()

        block, _ = BlockedUser.objects.get_or_create(blocker=request.user, blocked=target)
        return Response(
            BlockedUserSerializer(block, context={'viewer': request.user}).data,
            status=status.HTTP_201_CREATED,
        )


class UnblockView(APIView):
    """DELETE /api/social/blocks/<id>/"""
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = None

    def delete(self, request, pk):
        block = get_object_or_404(BlockedUser, pk=pk, blocker=request.user)
        block.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
