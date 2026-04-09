from rest_framework import viewsets, permissions
from .models import CulturalRule, LocalEvent
from .serializers import CulturalRuleSerializer, LocalEventSerializer


class CulturalRuleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class   = CulturalRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = CulturalRule.objects.all()
        country = self.request.query_params.get('country')
        city    = self.request.query_params.get('city')
        if country:
            qs = qs.filter(country__iexact=country)
        if city:
            qs = qs.filter(city__iexact=city)
        return qs


class LocalEventViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class   = LocalEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = LocalEvent.objects.all()
        country = self.request.query_params.get('country')
        month   = self.request.query_params.get('month')
        if country:
            qs = qs.filter(country__iexact=country)
        if month:
            qs = qs.filter(start_month__lte=month, end_month__gte=month)
        return qs
