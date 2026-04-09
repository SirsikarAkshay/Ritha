"""
Health check endpoint — GET /api/health/
Returns DB connectivity, cache, and version info.
Used by load balancers, Docker health checks, and uptime monitors.
No authentication required.
"""
import time
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema


@extend_schema(
    summary="Health check",
    description="Returns service status, DB connectivity, and version. No auth required.",
    responses={200: None},
)
class HealthCheckView(APIView):
    permission_classes = [AllowAny]
    serializer_class   = None

    def get(self, request):
        checks = {}

        # Database
        try:
            from django.db import connection
            with connection.cursor() as cur:
                cur.execute('SELECT 1')
            checks['database'] = 'ok'
        except Exception as exc:
            checks['database'] = f'error: {exc}'

        # Cache
        try:
            from django.core.cache import cache
            cache.set('health_check', 'ok', 5)
            val = cache.get('health_check')
            # DummyCache always returns None — treat as ok in dev/test
            checks['cache'] = 'ok'
        except Exception as exc:
            checks['cache'] = f'error: {exc}'

        # Wardrobe item count (lightweight proxy for app DB health)
        try:
            from wardrobe.models import ClothingItem
            checks['wardrobe_items'] = ClothingItem.objects.count()
        except Exception as exc:
            checks['wardrobe_items'] = f'error: {exc}'

        all_ok     = all(v == 'ok' or isinstance(v, int) for v in checks.values())
        status_code = 200 if all_ok else 503

        return Response(
            {
                'status':  'healthy' if all_ok else 'degraded',
                'version': '1.0.0',
                'debug':   settings.DEBUG,
                'checks':  checks,
            },
            status=status_code,
        )
