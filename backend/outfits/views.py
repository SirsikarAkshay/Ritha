import datetime
from collections import Counter

from django.db.models import Q, Count, Avg, Case, When, FloatField
from rest_framework import viewsets, permissions, decorators, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema_view, extend_schema
from .models import OutfitRecommendation, OutfitItem
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
        date_str = request.query_params.get('date', datetime.date.today().isoformat())
        try:
            date = datetime.date.fromisoformat(date_str)
        except ValueError:
            return Response({'detail': 'Invalid date format. Use YYYY-MM-DD.'}, status=400)

        rec = OutfitRecommendation.objects.filter(
            user=request.user, date=date, source='daily'
        ).prefetch_related('outfititem_set__clothing_item').first()

        if rec:
            return Response(OutfitRecommendationSerializer(rec).data)

        return Response(
            {'detail': 'No daily recommendation found for this date. '
                       'POST to /api/agents/daily-look/ to generate one.'},
            status=404
        )

    @decorators.action(detail=False, methods=['get'])
    def weekly(self, request):
        today = datetime.date.today()
        end = today + datetime.timedelta(days=6)
        recs = OutfitRecommendation.objects.filter(
            user=request.user, date__gte=today, date__lte=end, source='daily',
        ).prefetch_related('outfititem_set__clothing_item').order_by('date')
        data = OutfitRecommendationSerializer(recs, many=True).data
        days = []
        for i in range(7):
            d = today + datetime.timedelta(days=i)
            rec = next((r for r in data if r['date'] == d.isoformat()), None)
            days.append({
                'date': d.isoformat(),
                'day_label': d.strftime('%A'),
                'recommendation': rec,
            })
        return Response(days)

    @decorators.action(detail=True, methods=['patch'], url_path='feedback')
    def feedback(self, request, pk=None):
        """
        Accept or reject a recommendation, optionally with item-level feedback.
        Body: {
            "accepted": true|false,
            "item_feedback": [{"clothing_item": 5, "liked": true}, ...]  (optional)
        }
        """
        rec = self.get_object()
        accepted = request.data.get('accepted')
        if accepted is None:
            return Response({'detail': '"accepted" field required (true or false).'}, status=400)

        rec.accepted = bool(accepted)
        rec.save(update_fields=['accepted'])

        item_feedback = request.data.get('item_feedback', [])
        if item_feedback:
            for fb in item_feedback:
                ci_id = fb.get('clothing_item')
                liked = fb.get('liked')
                if ci_id is not None and liked is not None:
                    OutfitItem.objects.filter(
                        outfit=rec, clothing_item_id=ci_id
                    ).update(liked=bool(liked))

        if bool(accepted):
            for oi in rec.outfititem_set.select_related('clothing_item').all():
                item = oi.clothing_item
                item.times_worn = (item.times_worn or 0) + 1
                item.last_worn = rec.date
                item.save(update_fields=['times_worn', 'last_worn'])

        return Response(OutfitRecommendationSerializer(rec).data)


class OutfitHistoryView(generics.ListAPIView):
    """
    GET /api/outfits/history/
    Past outfit recommendations, newest first.
    Query params: ?days=90 (default 90), ?source=daily|trip, ?status=accepted|rejected|pending
    """
    serializer_class   = OutfitRecommendationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        from django.utils import timezone
        days   = int(self.request.query_params.get('days', 90))
        source = self.request.query_params.get('source', '')
        status = self.request.query_params.get('status', '')
        since  = timezone.now() - datetime.timedelta(days=days)
        qs = OutfitRecommendation.objects\
            .filter(user=self.request.user, date__gte=since.date())\
            .prefetch_related('outfititem_set__clothing_item')\
            .order_by('-date')
        if source:
            qs = qs.filter(source=source)
        if status == 'accepted':
            qs = qs.filter(accepted=True)
        elif status == 'rejected':
            qs = qs.filter(accepted=False)
        elif status == 'pending':
            qs = qs.filter(accepted__isnull=True)
        return qs


class OutfitPreferencesView(APIView):
    """
    GET /api/outfits/preferences/
    Computed user preferences from feedback history — used by the recommendation
    engine and shown in the UI as stats.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        recs = OutfitRecommendation.objects.filter(
            user=request.user, accepted__isnull=False
        ).prefetch_related('outfititem_set__clothing_item')

        total = recs.count()
        accepted = recs.filter(accepted=True).count()
        rejected = recs.filter(accepted=False).count()

        if total == 0:
            return Response({
                'total_recommendations': 0,
                'accepted': 0,
                'rejected': 0,
                'acceptance_rate': None,
                'preferred_categories': [],
                'avoided_categories': [],
                'preferred_colors': [],
                'preferred_formalities': [],
                'item_scores': {},
            })

        cat_accepted = Counter()
        cat_rejected = Counter()
        color_accepted = Counter()
        formality_accepted = Counter()
        item_scores = {}

        for rec in recs:
            for oi in rec.outfititem_set.all():
                ci = oi.clothing_item
                cat = ci.category
                if rec.accepted:
                    cat_accepted[cat] += 1
                else:
                    cat_rejected[cat] += 1

                if rec.accepted:
                    colors = ci.colors if isinstance(ci.colors, list) else []
                    for c in colors:
                        if isinstance(c, str) and c.strip():
                            color_accepted[c.lower().strip()] += 1
                    if ci.formality:
                        formality_accepted[ci.formality] += 1

                ci_id = ci.id
                if ci_id not in item_scores:
                    item_scores[ci_id] = {'accepted': 0, 'rejected': 0, 'liked': 0, 'disliked': 0}
                if rec.accepted:
                    item_scores[ci_id]['accepted'] += 1
                else:
                    item_scores[ci_id]['rejected'] += 1
                if oi.liked is True:
                    item_scores[ci_id]['liked'] += 1
                elif oi.liked is False:
                    item_scores[ci_id]['disliked'] += 1

        all_cats = set(cat_accepted.keys()) | set(cat_rejected.keys())
        cat_rates = {}
        for cat in all_cats:
            a = cat_accepted.get(cat, 0)
            r = cat_rejected.get(cat, 0)
            cat_rates[cat] = round(a / (a + r), 3) if (a + r) > 0 else 0.5

        preferred = sorted(cat_rates, key=cat_rates.get, reverse=True)[:5]
        avoided = sorted(cat_rates, key=cat_rates.get)[:3]

        return Response({
            'total_recommendations': total,
            'accepted': accepted,
            'rejected': rejected,
            'acceptance_rate': round(accepted / total, 3) if total else None,
            'preferred_categories': [{'category': c, 'rate': cat_rates[c]} for c in preferred],
            'avoided_categories': [{'category': c, 'rate': cat_rates[c]} for c in avoided if cat_rates[c] < 0.5],
            'preferred_colors': [{'color': c, 'count': n} for c, n in color_accepted.most_common(8)],
            'preferred_formalities': [{'formality': f, 'count': n} for f, n in formality_accepted.most_common(5)],
            'item_scores': {
                str(k): v for k, v in sorted(
                    item_scores.items(),
                    key=lambda x: x[1]['accepted'] - x[1]['rejected'],
                    reverse=True,
                )[:20]
            },
        })
