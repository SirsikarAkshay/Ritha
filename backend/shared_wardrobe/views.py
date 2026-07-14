"""
REST endpoints for shared wardrobes.

All mutations broadcast to the per-wardrobe channels group so connected
clients see updates live.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from social.models import Connection

from .models import (
    InvitationStatus,
    MemberRole,
    SharedWardrobe,
    SharedWardrobeInvitation,
    SharedWardrobeItem,
    SharedWardrobeMember,
)
from .serializers import (
    SharedWardrobeInvitationSerializer,
    SharedWardrobeItemSerializer,
    SharedWardrobeMemberSerializer,
    SharedWardrobeSerializer,
)

logger = logging.getLogger(__name__)
User = get_user_model()


def _broadcast(wardrobe_id: int, event_type: str, payload: dict):
    """Broadcast failures must not fail the request — DB state is authoritative."""
    try:
        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            f"sharedwardrobe_{wardrobe_id}",
            {"type": "wardrobe.event", "event_type": event_type, "payload": payload},
        )
    except Exception as e:
        logger.warning("Wardrobe broadcast failed for %s/%s: %s", wardrobe_id, event_type, e)


def _require_member(wardrobe, user):
    if not wardrobe.is_member(user):
        return Response(
            {"error": {"code": "forbidden", "message": "You are not a member of this wardrobe."}},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


def _require_owner(wardrobe, user):
    if wardrobe.member_role(user) != MemberRole.OWNER:
        return Response(
            {"error": {"code": "forbidden", "message": "Only the owner can do this."}},
            status=status.HTTP_403_FORBIDDEN,
        )
    return None


# ── Wardrobes list / create ───────────────────────────────────────────────────
class WardrobeListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        wardrobes = SharedWardrobe.objects.filter(members__user=request.user).distinct()
        data = SharedWardrobeSerializer(wardrobes, many=True, context={"request": request}).data
        return Response(data)

    def post(self, request):
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response(
                {"error": {"code": "missing_fields", "message": "`name` is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        description = (request.data.get("description") or "").strip()

        with transaction.atomic():
            wardrobe = SharedWardrobe.objects.create(
                name=name,
                description=description,
                created_by=request.user,
            )
            SharedWardrobeMember.objects.create(
                wardrobe=wardrobe,
                user=request.user,
                role=MemberRole.OWNER,
            )

        return Response(
            SharedWardrobeSerializer(wardrobe, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )


# ── Wardrobe detail / delete ──────────────────────────────────────────────────
class WardrobeDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get(self, pk):
        try:
            return SharedWardrobe.objects.get(pk=pk)
        except SharedWardrobe.DoesNotExist:
            return None

    def get(self, request, pk):
        wardrobe = self._get(pk)
        if not wardrobe:
            return Response({"error": {"code": "not_found", "message": "Not found."}}, status=status.HTTP_404_NOT_FOUND)
        err = _require_member(wardrobe, request.user)
        if err:
            return err
        return Response(SharedWardrobeSerializer(wardrobe, context={"request": request}).data)

    def delete(self, request, pk):
        wardrobe = self._get(pk)
        if not wardrobe:
            return Response({"error": {"code": "not_found", "message": "Not found."}}, status=status.HTTP_404_NOT_FOUND)
        err = _require_owner(wardrobe, request.user)
        if err:
            return err
        wardrobe.delete()
        _broadcast(pk, "wardrobe_deleted", {"wardrobe_id": pk})
        return Response({"status": "deleted"})


# ── Members / Invitations ─────────────────────────────────────────────────────
class MemberAddView(APIView):
    """POST /api/shared-wardrobes/<pk>/members/  body: { user_id }
    Sends an invitation instead of directly adding. The invitee must accept."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            wardrobe = SharedWardrobe.objects.get(pk=pk)
        except SharedWardrobe.DoesNotExist:
            return Response({"error": {"code": "not_found", "message": "Not found."}}, status=status.HTTP_404_NOT_FOUND)
        err = _require_owner(wardrobe, request.user)
        if err:
            return err

        target_id = request.data.get("user_id")
        if not target_id:
            return Response(
                {"error": {"code": "missing_fields", "message": "`user_id` is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            target = User.objects.get(id=target_id, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "User not found."}}, status=status.HTTP_404_NOT_FOUND
            )

        if not Connection.are_connected(request.user, target):
            return Response(
                {"error": {"code": "not_connected", "message": "You can only invite users you are connected with."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        if wardrobe.is_member(target):
            return Response(
                {"error": {"code": "already_member", "message": "User is already a member."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing = SharedWardrobeInvitation.objects.filter(
            wardrobe=wardrobe,
            invitee=target,
            status=InvitationStatus.PENDING,
        ).first()
        if existing:
            return Response(
                {"error": {"code": "already_invited", "message": "Invitation already pending."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invitation = SharedWardrobeInvitation.objects.create(
            wardrobe=wardrobe,
            invited_by=request.user,
            invitee=target,
        )
        payload = SharedWardrobeInvitationSerializer(invitation, context={"request": request}).data
        return Response(payload, status=status.HTTP_201_CREATED)


class InvitationListView(APIView):
    """GET /api/shared-wardrobes/invitations/ — pending invitations for the current user."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        invitations = SharedWardrobeInvitation.objects.filter(
            invitee=request.user,
            status=InvitationStatus.PENDING,
        ).select_related("wardrobe", "invited_by", "invitee")
        data = SharedWardrobeInvitationSerializer(invitations, many=True, context={"request": request}).data
        return Response(data)


class InvitationRespondView(APIView):
    """POST /api/shared-wardrobes/invitations/<pk>/respond/  body: { action: "accept"|"decline" }"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            invitation = SharedWardrobeInvitation.objects.select_related("wardrobe").get(
                pk=pk,
                invitee=request.user,
                status=InvitationStatus.PENDING,
            )
        except SharedWardrobeInvitation.DoesNotExist:
            return Response(
                {"error": {"code": "not_found", "message": "Invitation not found."}}, status=status.HTTP_404_NOT_FOUND
            )

        action = (request.data.get("action") or "").lower()
        if action not in ("accept", "decline"):
            return Response(
                {"error": {"code": "invalid_action", "message": 'action must be "accept" or "decline".'}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        if action == "decline":
            invitation.status = InvitationStatus.DECLINED
            invitation.resolved_at = now
            invitation.save(update_fields=["status", "resolved_at"])
            return Response({"status": "declined"})

        with transaction.atomic():
            invitation.status = InvitationStatus.ACCEPTED
            invitation.resolved_at = now
            invitation.save(update_fields=["status", "resolved_at"])
            member, _ = SharedWardrobeMember.objects.get_or_create(
                wardrobe=invitation.wardrobe,
                user=request.user,
                defaults={"role": MemberRole.EDITOR},
            )

        payload = SharedWardrobeMemberSerializer(member, context={"request": request}).data
        _broadcast(invitation.wardrobe_id, "member_added", payload)
        return Response({"status": "accepted", "member": payload})


class MemberRemoveView(APIView):
    """DELETE /api/shared-wardrobes/<pk>/members/<user_id>/  — owner removes anyone, self-remove allowed."""

    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk, user_id):
        try:
            wardrobe = SharedWardrobe.objects.get(pk=pk)
        except SharedWardrobe.DoesNotExist:
            return Response({"error": {"code": "not_found", "message": "Not found."}}, status=status.HTTP_404_NOT_FOUND)

        is_owner = wardrobe.member_role(request.user) == MemberRole.OWNER
        is_self = int(user_id) == request.user.pk
        if not (is_owner or is_self):
            return Response(
                {"error": {"code": "forbidden", "message": "Only the owner can remove other members."}},
                status=status.HTTP_403_FORBIDDEN,
            )

        member = wardrobe.members.filter(user_id=user_id).first()
        if not member:
            return Response(
                {"error": {"code": "not_found", "message": "Member not found."}}, status=status.HTTP_404_NOT_FOUND
            )

        if member.role == MemberRole.OWNER:
            return Response(
                {"error": {"code": "owner", "message": "Cannot remove the owner. Delete the wardrobe instead."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        member.delete()
        _broadcast(wardrobe.id, "member_removed", {"user_id": int(user_id)})
        return Response({"status": "removed"})


# ── Join by shareable link ────────────────────────────────────────────────────
class WardrobeInviteLinkView(APIView):
    """POST /api/shared-wardrobes/<pk>/invite-link/ — get (minting on first use) the
    shareable join token. Any member can share the link with their crew."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            wardrobe = SharedWardrobe.objects.get(pk=pk)
        except SharedWardrobe.DoesNotExist:
            return Response({"error": {"code": "not_found", "message": "Not found."}}, status=status.HTTP_404_NOT_FOUND)
        err = _require_member(wardrobe, request.user)
        if err:
            return err
        token = wardrobe.ensure_invite_token()
        return Response({"token": token, "join_path": f"/join/{token}", "wardrobe_id": wardrobe.id})


class WardrobeJoinView(APIView):
    """POST /api/shared-wardrobes/join/  body: { token } — join a wardrobe via its share link."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        token = (request.data.get("token") or "").strip()
        if not token:
            return Response(
                {"error": {"code": "missing_fields", "message": "`token` is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            wardrobe = SharedWardrobe.objects.get(invite_token=token)
        except SharedWardrobe.DoesNotExist:
            return Response(
                {"error": {"code": "invalid_token", "message": "This invite link is invalid or has expired."}},
                status=status.HTTP_404_NOT_FOUND,
            )

        member, created = SharedWardrobeMember.objects.get_or_create(
            wardrobe=wardrobe, user=request.user, defaults={"role": MemberRole.EDITOR}
        )
        if created:
            payload = SharedWardrobeMemberSerializer(member, context={"request": request}).data
            _broadcast(wardrobe.id, "member_added", payload)
        return Response(
            {
                "status": "joined",
                "already_member": not created,
                "wardrobe": SharedWardrobeSerializer(wardrobe, context={"request": request}).data,
            }
        )


# ── Items ─────────────────────────────────────────────────────────────────────
class ItemListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            wardrobe = SharedWardrobe.objects.get(pk=pk)
        except SharedWardrobe.DoesNotExist:
            return Response({"error": {"code": "not_found", "message": "Not found."}}, status=status.HTTP_404_NOT_FOUND)
        err = _require_member(wardrobe, request.user)
        if err:
            return err
        items = wardrobe.items.all()
        return Response(SharedWardrobeItemSerializer(items, many=True, context={"request": request}).data)

    def post(self, request, pk):
        try:
            wardrobe = SharedWardrobe.objects.get(pk=pk)
        except SharedWardrobe.DoesNotExist:
            return Response({"error": {"code": "not_found", "message": "Not found."}}, status=status.HTTP_404_NOT_FOUND)
        err = _require_member(wardrobe, request.user)
        if err:
            return err

        name = (request.data.get("name") or "").strip()
        if not name:
            return Response(
                {"error": {"code": "missing_fields", "message": "`name` is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        item = SharedWardrobeItem.objects.create(
            wardrobe=wardrobe,
            added_by=request.user,
            name=name,
            category=request.data.get("category") or "other",
            brand=(request.data.get("brand") or "").strip(),
            image_url=(request.data.get("image_url") or "").strip(),
            notes=(request.data.get("notes") or "").strip(),
        )
        payload = SharedWardrobeItemSerializer(item, context={"request": request}).data
        _broadcast(wardrobe.id, "item_added", payload)
        return Response(payload, status=status.HTTP_201_CREATED)


class ItemDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_wardrobe_and_item(self, request, pk, item_id):
        try:
            wardrobe = SharedWardrobe.objects.get(pk=pk)
        except SharedWardrobe.DoesNotExist:
            return (
                None,
                None,
                Response(
                    {"error": {"code": "not_found", "message": "Not found."}},
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )
        err = _require_member(wardrobe, request.user)
        if err:
            return None, None, err
        item = wardrobe.items.filter(pk=item_id).first()
        if not item:
            return (
                None,
                None,
                Response(
                    {"error": {"code": "not_found", "message": "Item not found."}},
                    status=status.HTTP_404_NOT_FOUND,
                ),
            )
        return wardrobe, item, None

    def _require_edit_permission(self, wardrobe, item, user):
        is_owner = wardrobe.member_role(user) == MemberRole.OWNER
        if not is_owner and item.added_by_id != user.pk:
            return Response(
                {
                    "error": {
                        "code": "forbidden",
                        "message": "Only the wardrobe owner or the item adder can modify this.",
                    }
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    def patch(self, request, pk, item_id):
        wardrobe, item, err = self._get_wardrobe_and_item(request, pk, item_id)
        if err:
            return err
        perm_err = self._require_edit_permission(wardrobe, item, request.user)
        if perm_err:
            return perm_err

        EDITABLE = ("name", "category", "brand", "image_url", "notes")
        updated_fields = []
        for field in EDITABLE:
            if field in request.data:
                setattr(
                    item, field, (request.data[field] or "").strip() if field != "category" else request.data[field]
                )
                updated_fields.append(field)
        if updated_fields:
            item.save(update_fields=updated_fields)

        payload = SharedWardrobeItemSerializer(item, context={"request": request}).data
        _broadcast(wardrobe.id, "item_updated", payload)
        return Response(payload)

    def delete(self, request, pk, item_id):
        wardrobe, item, err = self._get_wardrobe_and_item(request, pk, item_id)
        if err:
            return err
        perm_err = self._require_edit_permission(wardrobe, item, request.user)
        if perm_err:
            return perm_err

        item.delete()
        _broadcast(wardrobe.id, "item_removed", {"item_id": int(item_id)})
        return Response({"status": "removed"})
