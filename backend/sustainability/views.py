from rest_framework import viewsets, permissions, generics
from drf_spectacular.utils import extend_schema_view, extend_schema
from rest_framework.response import Response
from .models import SustainabilityLog, UserSustainabilityProfile
from .serializers import SustainabilityLogSerializer, UserSustainabilityProfileSerializer


@extend_schema_view(
    retrieve=extend_schema(parameters=[]),
    update=extend_schema(parameters=[]),
    partial_update=extend_schema(parameters=[]),
    destroy=extend_schema(parameters=[]),
)
class SustainabilityLogViewSet(viewsets.ModelViewSet):
    lookup_field = "pk"
    lookup_value_regex = r"[0-9]+"
    serializer_class   = SustainabilityLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = SustainabilityLog.objects.filter(user=self.request.user)
        action = self.request.query_params.get('action')
        if action:
            qs = qs.filter(action=action)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SustainabilityTrackerView(generics.RetrieveAPIView):
    serializer_class   = UserSustainabilityProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, _ = UserSustainabilityProfile.objects.get_or_create(user=self.request.user)
        return profile
