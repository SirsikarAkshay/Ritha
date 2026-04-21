from rest_framework import viewsets, permissions, decorators
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework.response import Response
from django.db.models import Q
from .models import CalendarEvent, Trip, PackingChecklistItem
from .serializers import CalendarEventSerializer, TripSerializer, PackingChecklistItemSerializer
import datetime


@extend_schema_view(
    retrieve=extend_schema(parameters=[]),
    update=extend_schema(parameters=[]),
    partial_update=extend_schema(parameters=[]),
    destroy=extend_schema(parameters=[]),
)
class CalendarEventViewSet(viewsets.ModelViewSet):
    lookup_field = "pk"
    lookup_value_regex = r"[0-9]+"
    serializer_class   = CalendarEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs         = CalendarEvent.objects.filter(user=self.request.user).select_related('user')
        # Exclude events marked as cross-source duplicates
        qs = qs.exclude(raw_data__is_duplicate=True)
        date       = self.request.query_params.get('date')
        start_date = self.request.query_params.get('start_date')
        end_date   = self.request.query_params.get('end_date')
        if start_date:
            qs = qs.filter(start_time__date__gte=start_date)
        if end_date:
            qs = qs.filter(start_time__date__lte=end_date)
        if date and not (start_date or end_date):
            qs = qs.filter(start_time__date=date)
        return qs.order_by('start_time')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @decorators.action(detail=False, methods=['post'])
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
                days_behind=getattr(settings, 'CALENDAR_SYNC_DAYS_BEHIND', 7),
                days_ahead=getattr(settings, 'CALENDAR_SYNC_DAYS_AHEAD', 60),
            )
            results['google'] = r

        if user.apple_calendar_connected:
            from calendar_sync.apple_calendar import sync_events as apple_sync
            from django.conf import settings
            r = apple_sync(
                user,
                days_behind=getattr(settings, 'CALENDAR_SYNC_DAYS_BEHIND', 7),
                days_ahead=getattr(settings, 'CALENDAR_SYNC_DAYS_AHEAD', 60),
            )
            results['apple'] = r

        if user.outlook_calendar_connected:
            from calendar_sync.outlook_calendar import sync_events as outlook_sync
            r = outlook_sync(
                user,
                days_behind=getattr(settings, 'CALENDAR_SYNC_DAYS_BEHIND', 7),
                days_ahead=getattr(settings, 'CALENDAR_SYNC_DAYS_AHEAD', 60),
            )
            results['outlook'] = r

        if not results:
            return Response({
                'status':  'no_calendars_connected',
                'message': 'No calendars connected. Go to Profile → Account details to connect Google, Apple, or Outlook Calendar.',
            })

        total_created = sum(r.get('created', 0) for r in results.values() if isinstance(r, dict))
        total_updated = sum(r.get('updated', 0) for r in results.values() if isinstance(r, dict))

        return Response({
            'status':  'synced',
            'created': total_created,
            'updated': total_updated,
            'providers': results,
        })


@extend_schema_view(
    retrieve=extend_schema(parameters=[]),
    update=extend_schema(parameters=[]),
    partial_update=extend_schema(parameters=[]),
    destroy=extend_schema(parameters=[]),
)
class TripViewSet(viewsets.ModelViewSet):
    lookup_field = "pk"
    lookup_value_regex = r"[0-9]+"
    serializer_class   = TripSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return Trip.objects.filter(
            Q(user=user) | Q(shared_wardrobe__members__user=user)
        ).distinct().select_related('shared_wardrobe')

    def perform_create(self, serializer):
        sw_id = self.request.data.get('shared_wardrobe')
        if sw_id:
            from shared_wardrobe.models import SharedWardrobe
            try:
                sw = SharedWardrobe.objects.get(pk=sw_id)
            except SharedWardrobe.DoesNotExist:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({'shared_wardrobe': 'Shared wardrobe not found.'})
            if not sw.is_member(self.request.user):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('You are not a member of this shared wardrobe.')
        serializer.save(user=self.request.user)

    @decorators.action(detail=True, methods=['post', 'delete'], url_path='save-recommendation')
    def save_recommendation(self, request, pk=None):
        """Save or clear an AI recommendation on this trip."""
        trip = self.get_object()
        if request.method == 'DELETE':
            trip.saved_recommendation = None
            trip.save(update_fields=['saved_recommendation'])
            return Response({'status': 'cleared', 'trip_id': trip.id})
        recommendation = request.data.get('recommendation')
        if not recommendation:
            return Response({'detail': 'recommendation payload is required.'}, status=400)
        trip.saved_recommendation = recommendation
        trip.save(update_fields=['saved_recommendation'])
        return Response({'status': 'saved', 'trip_id': trip.id})


class PackingChecklistViewSet(viewsets.ModelViewSet):
    """
    CRUD for trip packing checklist items.
    Filter by trip: GET /api/itinerary/checklist/?trip_id=<id>
    Mark packed: PATCH /api/itinerary/checklist/<id>/ {"is_packed": true}
    """
    lookup_field         = 'pk'
    lookup_value_regex   = r'[0-9]+'
    permission_classes   = [permissions.IsAuthenticated]
    serializer_class     = PackingChecklistItemSerializer

    def get_queryset(self):
        qs      = PackingChecklistItem.objects.filter(trip__user=self.request.user)
        trip_id = self.request.query_params.get('trip_id')
        if trip_id:
            qs = qs.filter(trip_id=trip_id)
        return qs.select_related('clothing_item', 'trip')

    @decorators.action(detail=False, methods=['post'], url_path='from-packing-list')
    def from_packing_list(self, request):
        """
        Auto-populate checklist from an agent packing list result.
        Body: {"trip_id": 1, "item_ids": [1, 2, 3]}
        """
        from wardrobe.models import ClothingItem
        trip_id  = request.data.get('trip_id')
        item_ids = request.data.get('item_ids', [])

        if not trip_id:
            return Response({'detail': 'trip_id is required.'}, status=400)

        try:
            trip = Trip.objects.get(pk=trip_id, user=request.user)
        except Trip.DoesNotExist:
            return Response({'detail': 'Trip not found.'}, status=404)

        items = ClothingItem.objects.filter(pk__in=item_ids, user=request.user)
        created = []
        for item in items:
            obj, was_created = PackingChecklistItem.objects.get_or_create(
                trip=trip, clothing_item=item,
                defaults={'quantity': 1}
            )
            if was_created:
                created.append(obj.id)

        return Response({
            'trip_id':      trip.id,
            'items_added':  len(created),
            'total_items':  PackingChecklistItem.objects.filter(trip=trip).count(),
        })
