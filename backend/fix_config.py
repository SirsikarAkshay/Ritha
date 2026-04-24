"""
Run from your project root (where manage.py is):
  python fix_config.py
"""
import os, sys, subprocess

if not os.path.exists('manage.py'):
    print("❌ Run this from your project root (where manage.py is)")
    sys.exit(1)

# ── 1. Create config_view.py with all fields the frontend expects ─────────
config_view = '''from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


class ConfigView(APIView):
    """
    GET /api/config  — public configuration for the frontend.
    No authentication required.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        return Response({
            # Fields the frontend reads
            "auth_trusted_header":     None,   # not used in this setup
            "google_oauth_enabled":    bool(getattr(settings, "GOOGLE_CLIENT_ID", "")),
            "microsoft_oauth_enabled": bool(getattr(settings, "MICROSOFT_CLIENT_ID", "")),
            "mistral_enabled":         bool(getattr(settings, "MISTRAL_API_KEY", "")),
            "email_verification":      True,
            "version":                 "1.0.0",
            "environment":             "development" if settings.DEBUG else "production",
        })
'''

with open('ritha/config_view.py', 'w') as f:
    f.write(config_view)
print("✅ Created ritha/config_view.py")

# ── 2. Wire into urls.py ──────────────────────────────────────────────────
with open('ritha/urls.py') as f:
    urls = f.read()

changed = False

if 'from ritha.config_view import ConfigView' not in urls:
    urls = urls.replace(
        'from ritha.health import HealthCheckView',
        'from ritha.health import HealthCheckView\nfrom ritha.config_view import ConfigView'
    )
    changed = True

if "path('api/config'" not in urls:
    urls = urls.replace(
        "path('api/health/",
        "path('api/config',   ConfigView.as_view(),   name='config'),\n    path('api/health/"
    )
    changed = True

if changed:
    with open('ritha/urls.py', 'w') as f:
        f.write(urls)
    print("✅ Added GET /api/config to urls.py")
else:
    print("✅ urls.py already has /api/config")

# ── 3. Django check ───────────────────────────────────────────────────────
result = subprocess.run(
    [sys.executable, 'manage.py', 'check'],
    capture_output=True, text=True
)
if 'no issues' in result.stdout:
    print("✅ Django check passed — no issues")
else:
    print("⚠  Django check output:")
    print(result.stdout or result.stderr)

# ── 4. Quick live test ────────────────────────────────────────────────────
try:
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ritha.settings')
    django.setup()
    from django.test import Client
    import json
    c = Client(SERVER_NAME='localhost')
    r = c.get('/api/config')
    data = json.loads(r.content)
    assert 'auth_trusted_header' in data, "auth_trusted_header missing from response"
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    print(f"✅ GET /api/config → 200, auth_trusted_header={data['auth_trusted_header']!r}")
except Exception as e:
    print(f"⚠  Live test failed: {e}")

print()
print("Restart your server:  python manage.py runserver")
print("Rebuild frontend:     cd frontend && npm run build  (or npm run dev)")