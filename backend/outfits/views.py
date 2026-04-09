import datetime
from rest_framework import viewsets, permissions, decorators, generics
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework.response import Response
from .models import OutfitRecommendation
from .serializers import OutfitRecommendationSerializer


@extend_schema_view(
    retrieve=extend_schema(parameters=[]),
    update=extend_schema(parameters=[]),
    partial_update=extend_schema(parameters=[]),
    destroy=extend_schema(parameters=[]),
)
class OutfitRecommendationViewSet(viewsets.ModelViewSet):
    lookup_field = "pk"
    lookup_value_regex = r"[0-9]+"
    serializer_class   = OutfitRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs    = OutfitRecommendation.objects.filter(user=self.request.user)\
                    .prefetch_related('outfititem_set__clothing_item')
        trip  = self.request.query_params.get('trip_id')
        src   = self.request.query_params.get('source')
        date  = self.request.query_params.get('date')
        if trip:
            qs = qs.filter(trip_id=trip)
        if src:
            qs = qs.filter(source=src)
        if date:
            qs = qs.filter(date=date)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @decorators.action(detail=False, methods=['get'])
    def daily(self, request):
        """
        Return today's outfit recommendation.
        Query params:
          ?date=YYYY-MM-DD  (defaults to today)
        """
        date_str = request.query_params.get('date', datetime.date.today().isoformat())
        try:
            date = datetime.date.fromisoformat(date_str)
        except ValueError:
            return Response({'detail': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

        rec = OutfitRecommendation.objects.filter(
            user=request.user, date=date, source='daily'
        ).first()

        if rec:
            return Response(OutfitRecommendationSerializer(rec).data)

        return Response(
            {'detail': 'No daily recommendation found for this date. '
                       'POST to /api/agents/daily-look/ to generate one.'},
            status=404
        )

    @decorators.action(detail=True, methods=['patch'], url_path='feedback')
    def feedback(self, request, pk=None):
        """
        Accept or reject a recommendation.
        Body: {"accepted": true|false}
        """
        rec = self.get_object()
        accepted = request.data.get('accepted')
        if accepted is None:
            return Response({'detail': '"accepted" field required (true or false).'}, status=400)
        rec.accepted = bool(accepted)
        rec.save()
        return Response({'id': rec.id, 'accepted': rec.accepted})

class OutfitHistoryView(generics.ListAPIView):
    """
    GET /api/outfits/history/
    Past accepted outfit recommendations, newest first.
    Query params: ?days=30 (default 30), ?source=daily|trip
    """
    serializer_class   = OutfitRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from django.utils import timezone
        import datetime
        days   = int(self.request.query_params.get('days', 30))
        source = self.request.query_params.get('source', '')
        since  = timezone.now() - datetime.timedelta(days=days)
        qs = OutfitRecommendation.objects\
            .filter(user=self.request.user, date__gte=since.date())\
            .prefetch_related('outfititem_set__clothing_item')\
            .order_by('-date')
        if source:
            qs = qs.filter(source=source)
        return qs
