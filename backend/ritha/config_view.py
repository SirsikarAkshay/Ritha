from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


class ConfigView(APIView):
    """GET /api/config — public config the frontend reads on startup."""
    permission_classes    = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({
            "auth_trusted_header":     None,
            "google_oauth_enabled":    bool(getattr(settings, "GOOGLE_CLIENT_ID", "")),
            "microsoft_oauth_enabled": bool(getattr(settings, "MICROSOFT_CLIENT_ID", "")),
            "mistral_enabled":         bool(getattr(settings, "MISTRAL_API_KEY", "")),
            "email_verification":      True,
            "version":                 "1.0.0",
            "environment":             "development" if settings.DEBUG else "production",
        })
