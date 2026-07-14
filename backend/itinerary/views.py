from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import decorators, permissions, viewsets
from rest_framework.response import Response

from .models import CalendarEvent, PackingChecklistItem, SavedShoppingItem, Trip
from .serializers import (
    CalendarEventSerializer,
    PackingChecklistItemSerializer,
    SavedShoppingItemSerializer,
    TripSerializer,
)


@extend_schema_view(
    retrieve=extend_schema(parameters=[]),
    update=extend_schema(parameters=[]),
    partial_update=extend_schema(parameters=[]),
    destroy=extend_schema(parameters=[]),
)
class CalendarEventViewSet(viewsets.ModelViewSet):
    lookup_field = "pk"
    lookup_value_regex = r"[0-9]+"
    serializer_class = CalendarEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = CalendarEvent.objects.filter(user=self.request.user).select_related("user")
        # Exclude events marked as cross-source duplicates
        qs = qs.exclude(raw_data__is_duplicate=True)
        date = self.request.query_params.get("date")
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            qs = qs.filter(start_time__date__gte=start_date)
        if end_date:
            qs = qs.filter(start_time__date__lte=end_date)
        if date and not (start_date or end_date):
            qs = qs.filter(start_time__date=date)
        return qs.order_by("start_time")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @decorators.action(detail=False, methods=["post"])
    def sync(self, request):
        """
        Sync all connected calendars (Google + Apple) for this user.
        Returns combined results from each provider.
        """
        user = request.user
        results = {}

        if user.google_calendar_connected:
            from calendar_sync.google_calendar import sync_events as google_sync
            from django.conf import settings

            r = google_sync(
                user,
                days_behind=getattr(settings, "CALENDAR_SYNC_DAYS_BEHIND", 7),
                days_ahead=getattr(settings, "CALENDAR_SYNC_DAYS_AHEAD", 60),
            )
            results["google"] = r

        if user.apple_calendar_connected:
            from calendar_sync.apple_calendar import sync_events as apple_sync
            from django.conf import settings

            r = apple_sync(
                user,
                days_behind=getattr(settings, "CALENDAR_SYNC_DAYS_BEHIND", 7),
                days_ahead=getattr(settings, "CALENDAR_SYNC_DAYS_AHEAD", 60),
            )
            results["apple"] = r

        if user.outlook_calendar_connected:
            from calendar_sync.outlook_calendar import sync_events as outlook_sync

            r = outlook_sync(
                user,
                days_behind=getattr(settings, "CALENDAR_SYNC_DAYS_BEHIND", 7),
                days_ahead=getattr(settings, "CALENDAR_SYNC_DAYS_AHEAD", 60),
            )
            results["outlook"] = r

        if not results:
            return Response(
                {
                    "status": "no_calendars_connected",
                    "message": "No calendars connected. Go to Profile → Account details to connect Google, Apple, or Outlook Calendar.",
                }
            )

        total_created = sum(r.get("created", 0) for r in results.values() if isinstance(r, dict))
        total_updated = sum(r.get("updated", 0) for r in results.values() if isinstance(r, dict))

        return Response(
            {
                "status": "synced",
                "created": total_created,
                "updated": total_updated,
                "providers": results,
            }
        )


@extend_schema_view(
    retrieve=extend_schema(parameters=[]),
    update=extend_schema(parameters=[]),
    partial_update=extend_schema(parameters=[]),
    destroy=extend_schema(parameters=[]),
)
class TripViewSet(viewsets.ModelViewSet):
    lookup_field = "pk"
    lookup_value_regex = r"[0-9]+"
    serializer_class = TripSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return (
            Trip.objects.filter(Q(user=user) | Q(shared_wardrobe__members__user=user))
            .distinct()
            .select_related("shared_wardrobe")
        )

    def perform_create(self, serializer):
        sw_id = self.request.data.get("shared_wardrobe")
        if sw_id:
            from shared_wardrobe.models import SharedWardrobe

            try:
                sw = SharedWardrobe.objects.get(pk=sw_id)
            except SharedWardrobe.DoesNotExist:
                from rest_framework.exceptions import ValidationError

                raise ValidationError({"shared_wardrobe": "Shared wardrobe not found."}) from None
            if not sw.is_member(self.request.user):
                from rest_framework.exceptions import PermissionDenied

                raise PermissionDenied("You are not a member of this shared wardrobe.")
        serializer.save(user=self.request.user)

    def _require_owner(self, trip):
        # get_queryset intentionally includes trips shared with the user (read access),
        # so every WRITE path must re-check ownership — a collaborator must not be able
        # to edit/delete/overwrite the trip owner's record.
        if trip.user_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Only the trip owner can modify this trip.")

    def perform_update(self, serializer):
        self._require_owner(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._require_owner(instance)
        instance.delete()

    @decorators.action(detail=True, methods=["post", "delete"], url_path="save-recommendation")
    def save_recommendation(self, request, pk=None):
        """Save or clear an AI recommendation on this trip."""
        trip = self.get_object()
        self._require_owner(trip)
        if request.method == "DELETE":
            trip.saved_recommendation = None
            trip.save(update_fields=["saved_recommendation"])
            return Response({"status": "cleared", "trip_id": trip.id})
        recommendation = request.data.get("recommendation")
        if not recommendation:
            return Response({"detail": "recommendation payload is required."}, status=400)
        trip.saved_recommendation = recommendation
        trip.save(update_fields=["saved_recommendation"])

        items_added = 0
        if trip.shared_wardrobe_id:
            items_added = self._push_items_to_shared_wardrobe(
                trip.shared_wardrobe,
                request.user,
                recommendation,
            )

        return Response(
            {
                "status": "saved",
                "trip_id": trip.id,
                "shared_wardrobe_items_added": items_added,
            }
        )

    @decorators.action(detail=True, methods=["post"], url_path="share")
    def share(self, request, pk=None):
        """
        Ensure this trip has a shared wardrobe (the collaboration hub) and return a
        join link. Powers the reel's "share one link, friends join the trip".
        """
        trip = self.get_object()
        self._require_owner(trip)
        from shared_wardrobe.models import MemberRole, SharedWardrobe, SharedWardrobeMember

        sw = trip.shared_wardrobe
        if sw is None:
            sw = SharedWardrobe.objects.create(
                name=trip.name or f"{trip.destination} trip",
                created_by=request.user,
            )
            SharedWardrobeMember.objects.get_or_create(
                wardrobe=sw, user=request.user, defaults={"role": MemberRole.OWNER}
            )
            trip.shared_wardrobe = sw
            trip.save(update_fields=["shared_wardrobe"])
        token = sw.ensure_invite_token()
        return Response({"trip_id": trip.id, "wardrobe_id": sw.id, "token": token, "join_path": f"/join/{token}"})

    @staticmethod
    def _push_items_to_shared_wardrobe(wardrobe, user, recommendation):
        from shared_wardrobe.models import SharedWardrobeItem
        from wardrobe.models import ClothingItem

        seen_ids = set()
        items_to_add = []

        def collect_matches(data):
            if isinstance(data, dict):
                for day in data.get("days", []):
                    for m in day.get("wardrobe_matches", []):
                        item = m.get("item", {})
                        if item.get("id") and item["id"] not in seen_ids:
                            seen_ids.add(item["id"])
                            items_to_add.append((item["id"], m.get("role", "other")))
                if data.get("multi_city") and isinstance(data.get("cities"), list):
                    for city_entry in data["cities"]:
                        collect_matches(city_entry.get("recommendation", {}))

        collect_matches(recommendation)
        if not items_to_add:
            return 0

        clothing_items = {
            ci.id: ci
            for ci in ClothingItem.objects.filter(
                id__in=[i[0] for i in items_to_add],
                user=user,  # only the acting user's own items — never leak another user's items
            )
        }

        existing_names = set(wardrobe.items.values_list("name", flat=True))

        created = 0
        for ci_id, role in items_to_add:
            ci = clothing_items.get(ci_id)
            if not ci or ci.name in existing_names:
                continue
            CATEGORY_MAP = {"top", "bottom", "dress", "outerwear", "footwear", "accessory", "other"}
            category = ci.category if ci.category in CATEGORY_MAP else "other"
            SharedWardrobeItem.objects.create(
                wardrobe=wardrobe,
                added_by=user,
                name=ci.name,
                category=category,
                brand=ci.brand or "",
                notes=f"Added from trip recommendation ({role})",
            )
            existing_names.add(ci.name)
            created += 1
        return created


class PackingChecklistViewSet(viewsets.ModelViewSet):
    """
    CRUD for trip packing checklist items.
    Filter by trip: GET /api/itinerary/checklist/?trip_id=<id>
    Mark packed: PATCH /api/itinerary/checklist/<id>/ {"is_packed": true}
    """

    lookup_field = "pk"
    lookup_value_regex = r"[0-9]+"
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PackingChecklistItemSerializer

    def get_queryset(self):
        qs = PackingChecklistItem.objects.filter(trip__user=self.request.user)
        trip_id = self.request.query_params.get("trip_id")
        if trip_id:
            qs = qs.filter(trip_id=trip_id)
        return qs.select_related("clothing_item", "trip")

    def _validate_ownership(self, serializer):
        # `trip` and `clothing_item` are client-supplied writable FKs — a user could
        # point them at another user's records. Enforce ownership on create/update.
        from rest_framework.exceptions import PermissionDenied

        trip = serializer.validated_data.get("trip")
        if trip is not None and trip.user_id != self.request.user.id:
            raise PermissionDenied("You can only add items to your own trips.")
        ci = serializer.validated_data.get("clothing_item")
        if ci is not None and ci.user_id != self.request.user.id:
            raise PermissionDenied("That wardrobe item isn't yours.")

    def perform_create(self, serializer):
        self._validate_ownership(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._validate_ownership(serializer)
        serializer.save()

    @decorators.action(detail=False, methods=["post"], url_path="from-packing-list")
    def from_packing_list(self, request):
        """
        Auto-populate checklist from an agent packing list result.
        Body: {"trip_id": 1, "item_ids": [1, 2, 3]}
        """
        from wardrobe.models import ClothingItem

        trip_id = request.data.get("trip_id")
        item_ids = request.data.get("item_ids", [])

        if not trip_id:
            return Response({"detail": "trip_id is required."}, status=400)

        try:
            trip = Trip.objects.get(pk=trip_id, user=request.user)
        except Trip.DoesNotExist:
            return Response({"detail": "Trip not found."}, status=404)

        items = ClothingItem.objects.filter(pk__in=item_ids, user=request.user)
        created = []
        for item in items:
            obj, was_created = PackingChecklistItem.objects.get_or_create(
                trip=trip, clothing_item=item, defaults={"quantity": 1}
            )
            if was_created:
                created.append(obj.id)

        return Response(
            {
                "trip_id": trip.id,
                "items_added": len(created),
                "total_items": PackingChecklistItem.objects.filter(trip=trip).count(),
            }
        )


@extend_schema_view(
    retrieve=extend_schema(parameters=[]),
    update=extend_schema(parameters=[]),
    partial_update=extend_schema(parameters=[]),
    destroy=extend_schema(parameters=[]),
)
class SavedShoppingItemViewSet(viewsets.ModelViewSet):
    """
    A user's "Remind me to buy this later" list.

    List (optionally per trip): GET /api/itinerary/shopping-list/?trip_id=<id>
    Save a suggestion:          POST /api/itinerary/shopping-list/
    Mark bought:                PATCH /api/itinerary/shopping-list/<id>/ {"purchased": true}
    Remove:                     DELETE /api/itinerary/shopping-list/<id>/
    """

    lookup_field = "pk"
    lookup_value_regex = r"[0-9]+"
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SavedShoppingItemSerializer

    def get_queryset(self):
        qs = SavedShoppingItem.objects.filter(user=self.request.user)
        trip_id = self.request.query_params.get("trip_id")
        if trip_id:
            qs = qs.filter(trip_id=trip_id)
        return qs.select_related("trip")

    def _validate_trip(self, serializer):
        # `trip` is a client-supplied writable FK — a user must not attach a saved
        # item to another user's trip.
        trip = serializer.validated_data.get("trip")
        if trip is not None and trip.user_id != self.request.user.id:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("You can only save items to your own trips.")

    def perform_create(self, serializer):
        self._validate_trip(serializer)
        serializer.save(user=self.request.user)

    def perform_update(self, serializer):
        self._validate_trip(serializer)
        serializer.save()
