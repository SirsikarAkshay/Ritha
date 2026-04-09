# Arokah Backend

> AI-powered personal stylist — daily outfit looks, trip planning, cultural intelligence.
> Django 6 · SQLite (dev) / PostgreSQL (prod) · DRF · JWT · OpenAPI

---

## Quick Start (Development)

```bash
# 1 — Clone and install
git clone https://github.com/your-username/arokah.git
cd arokah
pip install -r requirements.txt

# 2 — Environment
cp .env.example .env          # edit with your keys

# 3 — Database
python manage.py migrate
python manage.py seed_cultural_data
python manage.py createsuperuser

# 4 — Run
python manage.py runserver
```

Or, using Make:

```bash
make install && make migrate && make seed && make run
```

---

## API Documentation

| URL | Description |
|-----|-------------|
| `http://localhost:8000/api/docs/`   | Swagger UI (interactive) |
| `http://localhost:8000/api/redoc/`  | ReDoc (readable) |
| `http://localhost:8000/api/schema/` | OpenAPI 3.0 YAML download |
| `http://localhost:8000/admin/`      | Django Admin |

---

## Endpoint Reference

### Auth  `/api/auth/`

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| POST | `/register/` | ❌ | Register new user |
| POST | `/login/` | ❌ | Obtain JWT access + refresh tokens |
| POST | `/refresh/` | ❌ | Refresh access token |
| POST | `/logout/` | ✅ | Blacklist refresh token |
| GET / PATCH | `/me/` | ✅ | Get or update profile |
| POST | `/me/password/` | ✅ | Change password |
| DELETE | `/me/delete/` | ✅ | Delete account (GDPR erasure) |

### Wardrobe  `/api/wardrobe/`

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/items/` | ✅ | List items. Filter: `?category=` `?formality=` `?season=` `?q=` |
| POST | `/items/` | ✅ | Create clothing item |
| GET / PATCH / DELETE | `/items/{id}/` | ✅ | Retrieve / update / soft-delete item |
| POST | `/background-removal/` | ✅ | Upload photo → background removed (stub / live) |
| POST | `/receipt-import/` | ✅ | Parse shopping email → auto-create items |
| POST | `/luggage-weight/` | ✅ | Calculate weight + carry-on eligibility + CO₂ saving |

### Itinerary  `/api/itinerary/`

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET / POST | `/events/` | ✅ | List or create calendar events. Filter: `?date=YYYY-MM-DD` |
| POST | `/events/sync/` | ✅ | Sync from Google Calendar / Outlook |
| GET / PATCH / DELETE | `/events/{id}/` | ✅ | Event detail |
| GET / POST | `/trips/` | ✅ | List or create trips |
| GET / PATCH / DELETE | `/trips/{id}/` | ✅ | Trip detail |

> **Auto-classification**: events are automatically classified by type (workout, external meeting, social, travel, etc.) and formality from the title/description on save.

### Outfits  `/api/outfits/`

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/recommendations/` | ✅ | List recommendations. Filter: `?source=` `?trip_id=` `?date=` |
| GET | `/recommendations/daily/` | ✅ | Today's recommendation. Query: `?date=YYYY-MM-DD` |
| PATCH | `/recommendations/{id}/feedback/` | ✅ | Accept or reject: `{"accepted": true}` |

### Cultural  `/api/cultural/`

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/rules/` | ✅ | Etiquette rules. Filter: `?country=` `?city=` |
| GET | `/events/` | ✅ | Local events. Filter: `?country=` `?month=` |

### Sustainability  `/api/sustainability/`

| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/tracker/` | ✅ | User sustainability profile (total points, CO₂ saved) |
| GET / POST | `/logs/` | ✅ | Sustainability activity log. Filter: `?action=` |

### Agents  `/api/agents/`

All agents return `{"job_id": int, "status": "completed"|"failed", "output": {...}}`.
Rate-limited to **50 calls/user/day** in production.

| Method | URL | Description |
|--------|-----|-------------|
| POST | `/daily-look/` | Generate today's outfit from calendar + weather |
| POST | `/packing-list/` | Packing list for a trip (5-4-3-2-1 capsule) |
| POST | `/outfit-planner/` | Per-day outfit plan for a full trip |
| POST | `/conflict-detector/` | Detect weather/activity/outfit conflicts |
| POST | `/cultural-advisor/` | Clothing rules + local event notes for a destination |

### Weather  `/api/weather/`

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/weather/?lat=47.37&lon=8.54` | Forecast by coordinates |
| GET | `/weather/?location=Zurich` | Forecast by location name (geocoded) |
| GET | `/weather/?location=Tokyo&date=2026-04-01` | Forecast for a specific date |

> Powered by [Open-Meteo](https://open-meteo.com) — free, no API key required.

---

## Environment Variables

Copy `.env.example` to `.env`:

```env
# Database (SQLite for dev — leave as-is)
DATABASE_ENGINE=django.db.backends.sqlite3
DATABASE_NAME=db.sqlite3

# Security
SECRET_KEY=change-me-in-production
JWT_SECRET=change-me-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# AI (optional — stubs work without keys)
MISTRAL_API_KEY=your-key     # from console.mistral.ai — activates live AI agents

# Calendar integrations (optional)
GOOGLE_CALENDAR_API_KEY=...
GOOGLE_VISION_API_KEY=...

# Frontend CORS
WEB_APP_URL=http://localhost:3000
MOBILE_APP_URL=http://localhost:8081

# Media
MEDIA_ROOT=media/
MEDIA_URL=/media/
```

---

## AI Behaviour

Arokah uses **Mistral AI** for all agent intelligence. Agents operate in two modes:

| Mode | Condition | Behaviour |
|------|-----------|-----------|
| **Stub** | No key, or placeholder key | Rule-based logic, deterministic, no API calls |
| **Live** | Valid `MISTRAL_API_KEY` set in `.env` | Mistral API call with full wardrobe + calendar context |

All endpoints return identical JSON shapes in both modes — stubs are safe for development and testing.

### Mistral models

Configured in `arokah/services/mistral_client.py`:

| Model | Use case |
|-------|----------|
| `mistral-small-latest` | Default — fast, accurate for JSON tasks |
| `mistral-medium-latest` | Better reasoning for complex outfit logic |
| `mistral-large-latest` | Best results for multi-day trip planning |

Get your API key at [console.mistral.ai](https://console.mistral.ai/).

---

## Management Commands

```bash
# Seed cultural etiquette data (run once after migrate)
python manage.py seed_cultural_data
python manage.py seed_cultural_data --flush   # clear + re-seed

# Batch generate daily outfit recommendations (run daily via cron)
python manage.py generate_daily_looks
python manage.py generate_daily_looks --date 2026-04-01
python manage.py generate_daily_looks --user user@example.com
python manage.py generate_daily_looks --dry-run

# GDPR data export
python manage.py export_user_data --email user@example.com
python manage.py export_user_data --email user@example.com --output export.json

# OpenAPI schema
python manage.py spectacular --file openapi.yaml
```

---

## Running Tests

```bash
make test                   # full suite with verbose output
make test-fast              # stop on first failure
python -m pytest tests/ -k "wardrobe"    # run a specific group
python -m pytest tests/ --tb=short -q   # quiet mode
```

**Current test count: 131 passing**

---

## Docker (Production)

```bash
# Start full stack: API + cron + PostgreSQL + Redis
make docker-up

# View logs
make docker-logs

# Stop
make docker-down
```

Add these to your production `.env`:

```env
DB_NAME=arokah
DB_USER=arokah
DB_PASSWORD=your_secure_password
REDIS_URL=redis://redis:6379/0
DJANGO_SETTINGS_MODULE=arokah.settings_production
```

---

## Project Structure

```
arokah/
├── arokah/              # Project config
│   ├── settings.py         # Development settings
│   ├── settings_production.py  # Production overrides
│   ├── signals.py          # Cross-app signals
│   └── services/
│       ├── weather.py      # Open-Meteo integration
│       ├── event_classifier.py  # Rule-based event classifier
│       └── views.py        # /api/weather/ endpoint
├── auth_app/               # Custom user + JWT auth
├── wardrobe/               # Clothing item CRUD + utilities
├── itinerary/              # Calendar events + trips
├── outfits/                # Daily look recommendations
├── cultural/               # Etiquette rules + local events
├── sustainability/         # CO₂ tracking + points
├── agents/                 # AI agent orchestration
├── tests/                  # 131 tests across 13 test files
├── Dockerfile
├── docker-compose.yml
├── Makefile
├── requirements.txt        # Dev dependencies
└── requirements_prod.txt   # Production dependencies
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | Django 6 + Django REST Framework |
| Auth | JWT (SimpleJWT) + token blacklist |
| API Docs | drf-spectacular (OpenAPI 3.0) |
| Database | SQLite (dev) / PostgreSQL 16 (prod) |
| Cache / Throttle | In-memory (dev) / Redis 7 (prod) |
| AI | OpenAI GPT-4o-mini (optional) |
| Weather | Open-Meteo (free, no key) |
| Container | Docker + docker-compose |

---

**Arokah** — Dress for your day. Every day. 🌍✨
