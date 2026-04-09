#!/usr/bin/env python3
"""
Arokah diagnostic script.
Run this if you're getting 500 errors: python diagnose.py
"""
import sys, os, subprocess

print("=" * 60)
print("Arokah Diagnostics")
print("=" * 60)

errors = []
warnings = []

# ── Python version ──────────────────────────────────────────────────────
v = sys.version_info
ok = v.major == 3 and v.minor >= 10
print(f"\n{'✅' if ok else '❌'} Python {v.major}.{v.minor}.{v.micro}" + ('' if ok else ' — need 3.10+'))
if not ok:
    errors.append("Python 3.10+ required")

# ── Required packages ───────────────────────────────────────────────────
print("\nChecking packages:")
packages = [
    ('django',                   'Django'),
    ('rest_framework',           'djangorestframework'),
    ('rest_framework_simplejwt', 'djangorestframework-simplejwt'),
    ('corsheaders',              'django-cors-headers'),
    ('drf_spectacular',          'drf-spectacular'),
    ('cryptography',             'cryptography'),
    ('PIL',                      'Pillow'),
    ('mistralai',                'mistralai'),
    ('caldav',                   'caldav'),
    ('icalendar',                'icalendar'),
    ('google.oauth2',            'google-auth'),
    ('google_auth_oauthlib',     'google-auth-oauthlib'),
    ('googleapiclient',          'google-api-python-client'),
    ('msal',                     'msal'),
    ('dateutil',                 'python-dateutil'),
    ('pytz',                     'pytz'),
    ('dotenv',                   'python-dotenv'),
]
for module, pkg in packages:
    try:
        __import__(module)
        print(f"  ✅ {pkg}")
    except ImportError:
        print(f"  ❌ {pkg} — run: pip install {pkg}")
        errors.append(f"Missing package: {pkg}")

# ── .env file ───────────────────────────────────────────────────────────
print("\nChecking .env:")
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    print("  ✅ .env file found")
    with open(env_path) as f:
        env_content = f.read()
    required_vars = ['SECRET_KEY', 'DEBUG', 'ALLOWED_HOSTS']
    for var in required_vars:
        if var in env_content:
            print(f"  ✅ {var} set")
        else:
            print(f"  ⚠  {var} not in .env (using default)")
            warnings.append(f"{var} not set in .env")
else:
    print("  ❌ .env not found — copy .env.example to .env")
    errors.append(".env file missing")

# ── Django setup ─────────────────────────────────────────────────────────
print("\nChecking Django:")
try:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'arokah.settings')
    import django
    django.setup()
    print("  ✅ Django configured")
except Exception as e:
    print(f"  ❌ Django setup failed: {e}")
    errors.append(f"Django setup error: {e}")
    print("\n" + "="*60)
    print("RESULT: Fix the errors above first")
    sys.exit(1)

# ── Database / migrations ────────────────────────────────────────────────
print("\nChecking database:")
try:
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    print("  ✅ Database connection OK")
except Exception as e:
    print(f"  ❌ Database error: {e}")
    errors.append(f"Database error: {e}")

try:
    from django.core.management import call_command
    from io import StringIO
    out = StringIO()
    call_command('showmigrations', '--list', stdout=out)
    pending = [l for l in out.getvalue().splitlines() if '[ ]' in l]
    if pending:
        print(f"  ❌ {len(pending)} unapplied migration(s) — run: python manage.py migrate")
        for p in pending[:5]:
            print(f"     {p.strip()}")
        errors.append("Unapplied migrations")
    else:
        print("  ✅ All migrations applied")
except Exception as e:
    print(f"  ⚠  Could not check migrations: {e}")

# ── ALLOWED_HOSTS ────────────────────────────────────────────────────────
print("\nChecking ALLOWED_HOSTS:")
from django.conf import settings
hosts = settings.ALLOWED_HOSTS
print(f"  Current: {hosts}")
if not hosts or hosts == ['']:
    print("  ⚠  Empty ALLOWED_HOSTS — set to localhost,127.0.0.1 in .env")
    warnings.append("ALLOWED_HOSTS empty")
else:
    needed = ['localhost', '127.0.0.1']
    for h in needed:
        if h in hosts:
            print(f"  ✅ {h} allowed")
        else:
            print(f"  ⚠  {h} not in ALLOWED_HOSTS — add it to .env")
            warnings.append(f"{h} not in ALLOWED_HOSTS")

# ── Quick API test ───────────────────────────────────────────────────────
print("\nTesting endpoints:")
from django.test import Client
c = Client(SERVER_NAME='localhost')

import json
tests = [
    ('/api/health/', 'GET', None),
    ('/api/auth/register/', 'POST', {'email': 'diag@test.com', 'password': 'DiagTest99!'}),
    ('/api/auth/login/', 'POST', {'email': 'diag@test.com', 'password': 'wrong'}),
]

from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.filter(email='diag@test.com').delete()

for url, method, body in tests:
    try:
        if method == 'GET':
            r = c.get(url)
        else:
            r = c.post(url, json.dumps(body or {}), content_type='application/json')
        ok = r.status_code < 500
        print(f"  {'✅' if ok else '❌'} {method} {url} → {r.status_code}")
        if not ok:
            errors.append(f"{method} {url} returned {r.status_code}")
            try:
                print(f"     Body: {r.content.decode()[:300]}")
            except: pass
    except Exception as e:
        print(f"  ❌ {method} {url} → EXCEPTION: {e}")
        errors.append(f"{method} {url} exception: {e}")

User.objects.filter(email='diag@test.com').delete()

# ── Summary ──────────────────────────────────────────────────────────────
print("\n" + "="*60)
if errors:
    print(f"❌ {len(errors)} error(s) found:")
    for e in errors:
        print(f"   • {e}")
    print("\nFix the errors above, then run: python manage.py runserver")
elif warnings:
    print(f"⚠  {len(warnings)} warning(s) — server may work but check these:")
    for w in warnings:
        print(f"   • {w}")
    print("\nRun: python manage.py runserver")
else:
    print("✅ Everything looks good!")
    print("\nStart the backend: python manage.py runserver")
    print("Start the frontend: cd frontend && npm run dev")
    print("Open: http://localhost:3000")
print("="*60)