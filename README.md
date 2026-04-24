# Ritha

AI-powered wardrobe and travel fashion companion. Recommends outfits based on your calendar, weather, wardrobe, and destination — whether that's the office tomorrow or a multi-city trip next month.

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Django 5.2, Django REST Framework, SimpleJWT auth |
| **AI / LLM** | Mistral AI (cultural context, shopping suggestions, outfit notes) |
| **ML** | PyTorch + scikit-learn (fashion category co-occurrence model) |
| **Weather** | Open-Meteo forecast API + historical archive API (climatology fallback) |
| **Geocoding** | Open-Meteo geocoding (free, no API key) |
| **Web frontend** | React 18, Vite, React Router 6 |
| **Mobile app** | Flutter 3 / Dart 3 |
| **Real-time** | Django Channels + WebSocket |
| **Calendar sync** | Google Calendar (OAuth), Outlook (MSAL), CalDAV/iCal |
| **Task queue** | Celery + django-celery-beat |
| **Database** | SQLite (dev) / PostgreSQL (prod) |
| **Caching** | Django LocMemCache (dev) / Redis (prod) |

---

## Features

### Unified Recommendation Engine

The core of the app is a multi-signal recommendation pipeline that combines:

- **ML compatibility model** — trained co-occurrence matrix scores category pairings
- **Live weather** — Open-Meteo forecast with automatic climatology fallback for distant-future trips or unavailable regions (historical averages from past 5 years)
- **Cultural AI** — Mistral-powered etiquette rules, local events, dress codes, and highlights for any destination
- **Wardrobe matching** — items the user owns are matched first; gaps produce shopping suggestions with links

Results are cached per signal (cultural 24h, weather 30min, shopping 6h) and I/O-bound fetches run in parallel via `ThreadPoolExecutor`.

### Wardrobe

- Add clothing items with photo, category, color, formality, season tags
- AI background removal for garment photos
- Track wear count and last-worn date
- Shared wardrobes — create collaborative closets with other users, add/remove members and items

### Daily Looks

- Calendar-driven outfit suggestions based on synced events
- Smart event classification — parses event titles/descriptions to infer formality (e.g. "board review" → polished, "spin class" → activewear)
- Morning outfit notification support
- Wear-again intelligence to avoid repetition

### Trip Planner

- Create trips with structured **country + multi-city** fields
- Per-city outfit recommendations run in parallel and display in tabbed UI
- Multi-day outfit plans with day-by-day weather, wardrobe matches, and gap analysis
- Packing checklist linked to wardrobe items
- Save/clear AI recommendations per trip
- Weather shows `*` with footnote when based on historical averages instead of live forecast

### Cultural Guide

- Country + city destination search with place autocomplete (Open-Meteo geocoding, filtered by PCL/PPL feature codes)
- AI-powered cultural advice: dress code rules (severity-tagged), local events with clothing notes, must-visit places with what-to-wear tips
- Popular destination quick-select chips
- Tabbed result layout: etiquette, events, places, shopping

### Calendar & Itinerary

- Google Calendar, Outlook, and manual event sync
- Event type classification (meeting, workout, social, travel, wedding, interview, date, etc.)
- Formality auto-detection from event context

### Social / People

- User connections (follow/friend system)
- Shared wardrobes with member management
- Real-time messaging via WebSocket (Django Channels)

### Sustainability

- CO₂ weight savings tracker
- Wear-again rewards / gamification
- Eco-shop integration for sustainable brand suggestions

### Profile & Auth

- JWT authentication (access + refresh tokens)
- Email verification, password reset flow
- Google Calendar / Outlook / Apple Calendar connect/disconnect
- Push notification configuration

---

## Project Structure

```
ritha/
├── backend/
│   ├── agents/             # AI agent views, services, Celery tasks
│   │   └── services.py     # daily_look, packing_list, conflict_detector,
│   │                        # cultural_advisor, outfit_planner, smart_recommend
│   ├── ritha/             # Django project settings, URLs, WSGI
│   │   └── services/
│   │       ├── recommendation_engine.py   # Unified rec engine (ML + weather + cultural)
│   │       ├── weather.py                 # Open-Meteo forecast + climatology fallback
│   │       ├── mistral_client.py          # Mistral AI wrapper
│   │       └── event_classifier.py        # Calendar event type classifier
│   ├── auth_app/           # User model, JWT auth, email verification
│   ├── wardrobe/           # ClothingItem CRUD, image upload
│   ├── itinerary/          # CalendarEvent, Trip (country/cities/JSONField), PackingChecklist
│   ├── calendar_sync/      # Google, Outlook, CalDAV integrations
│   ├── outfits/            # Outfit history, daily look records
│   ├── cultural/           # Cultural etiquette data
│   ├── social/             # User connections
│   ├── shared_wardrobe/    # Collaborative wardrobes
│   ├── messaging/          # WebSocket chat (Django Channels)
│   ├── sustainability/     # CO₂ tracker, eco-metrics
│   └── ml/                 # Fashion ML model (train.py, inference.py, artifacts/)
├── frontend/               # React 18 + Vite web app
│   └── src/
│       ├── pages/          # Dashboard, Wardrobe, TripPlanner, Cultural, People, etc.
│       ├── components/     # PlaceAutocomplete, shared UI
│       └── api/            # API client (fetch wrapper with JWT refresh)
├── mobile_flutter/         # Flutter mobile app
│   └── lib/
│       ├── screens/        # All app screens (mirror of web pages)
│       ├── widgets/        # PlaceAutocompleteField, shared widgets
│       ├── api/            # HTTP + WebSocket client with token management
│       └── theme/          # App colors, typography
└── requirements.txt        # Python dependencies
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Flutter SDK 3.11+

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r ../requirements.txt

cp .env.example .env   # Add MISTRAL_API_KEY, SECRET_KEY, etc.

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Web Frontend

```bash
cd frontend
npm install
npm run dev            # Vite dev server at localhost:5173
```

### Mobile App

```bash
cd mobile_flutter
flutter pub get
flutter run
```

### Environment Variables

```
SECRET_KEY=…
MISTRAL_API_KEY=…           # Required for AI agents
REDIS_URL=redis://…         # Optional — enables Redis cache (else LocMem)
GOOGLE_CLIENT_ID=…          # For Google Calendar OAuth
GOOGLE_CLIENT_SECRET=…
MSAL_CLIENT_ID=…            # For Outlook OAuth
MSAL_CLIENT_SECRET=…
```

---

## API Endpoints

### Auth
- `POST /api/auth/register/` — Create account
- `POST /api/auth/login/` — JWT token pair
- `POST /api/auth/token/refresh/` — Refresh access token
- `POST /api/auth/verify-email/` — Email verification
- `POST /api/auth/forgot-password/` — Password reset request

### Wardrobe
- `GET/POST /api/wardrobe/items/` — List / add clothing items
- `PATCH/DELETE /api/wardrobe/items/:id/` — Update / remove item

### Itinerary
- `GET/POST /api/itinerary/events/` — Calendar events
- `GET/POST /api/itinerary/trips/` — Trips (supports `country`, `cities` JSON fields)
- `POST /api/itinerary/trips/:id/save-recommendation/` — Save AI recommendation
- `DELETE /api/itinerary/trips/:id/save-recommendation/` — Clear saved recommendation
- `GET/POST /api/itinerary/checklist/` — Packing checklist items

### AI Agents
- `POST /api/agents/daily-look/` — Today's outfit based on calendar + weather
- `POST /api/agents/packing-list/` — Trip packing list generator
- `POST /api/agents/outfit-planner/` — Multi-day outfit plan (5-4-3-2-1 capsule)
- `POST /api/agents/cultural-advisor/` — Cultural etiquette + dress code advice
- `POST /api/agents/conflict-detector/` — Schedule / weather / outfit conflict check
- `POST /api/agents/smart-recommend/` — Unified recommendation (ML + weather + cultural); supports `cities: [...]` for parallel multi-city recommendations

### Social
- `GET/POST /api/social/connections/` — User connections
- `GET/POST /api/shared-wardrobes/` — Shared wardrobe CRUD
- `WebSocket /ws/chat/:room/` — Real-time messaging

---

## Features To Do

### High Priority
- [x] Push notifications (morning outfit, trip reminders) — Firebase Cloud Messaging integrated
- [x] Receipt-to-closet import — paste shopping receipt/confirmation emails to auto-populate wardrobe (Mistral AI parsing)
- [x] Outfit history & acceptance feedback — outfit-level + item-level feedback, user preference stats, ML-personalized scoring
- [x] Apple Calendar (CalDAV) sync completion — full CalDAV sync, periodic auto-sync via Celery, cross-source event deduplication

### Medium Priority
- [ ] Luggage weight predictor — estimate bag weight from item materials
- [ ] Multi-context day solver — outfit transitions for days with mixed events (e.g. office → gym → dinner)
- [ ] Social vibe analysis — scrape location tags for local style context
- [ ] Wear-again rewards gamification — streak tracking, badges
- [ ] Offline mode for mobile — cache wardrobe and last recommendations locally

### Lower Priority
- [ ] CO₂ weight savings calculator — carbon impact of lighter luggage
- [ ] Eco-commerce integration — prioritize sustainable / rental brands in shopping suggestions
- [ ] AI background removal for garment photos — server-side processing pipeline
- [ ] Style learning — personalized model fine-tuning from user feedback over time
- [ ] Docker Compose production deployment config
- [ ] Comprehensive test suite — unit + integration tests for agents and recommendation engine

---

## License

MIT
