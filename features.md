# Ritha — Implemented Features

A complete inventory of features currently implemented in Ritha. Backend is Django + DRF + Channels; web frontend is React + Vite; mobile is Flutter.

---

## 1. Authentication & Accounts

| Feature | Description | Key files |
|---|---|---|
| Email registration & login | Email/password auth issuing JWT access + refresh tokens. | `backend/auth_app/views.py` (RegisterView, LoginView); `frontend/src/pages/LoginPage.jsx`, `Register.jsx` |
| Email verification | Token-based verification with resend support. | `backend/auth_app/views.py` (VerifyEmailView, ResendVerificationView); `backend/auth_app/email.py`; `frontend/src/pages/VerifyEmail.jsx` |
| Forgot / reset password | Tokenized reset flow plus in-app password change. | `backend/auth_app/views.py` (ForgotPasswordView, ResetPasswordView, PasswordChangeView); `frontend/src/pages/ForgotPassword.jsx`, `ResetPassword.jsx` |
| Profile management | Update first/last name, timezone; fetch current user. | `backend/auth_app/views.py` (MeView); `frontend/src/pages/ProfilePage.jsx` |
| Push notification token registration | Store FCM device tokens for notifications. | `backend/auth_app/views.py` (RegisterPushTokenView) |
| Account deletion | Permanently delete user and associated data. | `backend/auth_app/views.py` (DeleteAccountView); `frontend/src/pages/ProfilePage.jsx` |
| Rate limiting | Throttles on login (5/hr), password reset (3/hr), AI agents (5/hr). | `backend/auth_app/views.py`, `backend/agents/throttles.py` |

---

## 2. Wardrobe Management

| Feature | Description | Key files |
|---|---|---|
| Clothing item CRUD | Categories (top, bottom, dress, outerwear, footwear, accessory, activewear, formal), formality, seasons, colors, material, weight, brand. | `backend/wardrobe/models.py`, `views.py` (ClothingItemViewSet); `frontend/src/pages/WardrobePage.jsx` |
| AI image analysis | Upload photo; Mistral extracts name, category, formality, season, colors, material, brand. | `backend/wardrobe/views.py` (AnalyzeClothingImageView); `backend/ritha/services/mistral_client.py` |
| Background removal (stub) | Placeholder endpoint for future bg-removal integration. | `backend/wardrobe/views.py` (BackgroundRemovalView) |
| Receipt import | Paste a shopping receipt email; Mistral parses it into wardrobe items. | `backend/wardrobe/views.py` (ReceiptImportView); `frontend/src/pages/WardrobePage.jsx` |
| Bulk upload | Create up to 50 items in a single request. | `backend/wardrobe/views.py` (BulkWardrobeUploadView) |
| Filter & search | Filter by category/formality/season; free-text search on name, brand, material. | `backend/wardrobe/views.py`; `frontend/src/pages/WardrobePage.jsx` |
| Luggage weight calculator | Totals selected-item weight, checks carry-on eligibility by airline, estimates CO₂ savings. | `backend/wardrobe/views.py` (LuggageWeightView); `frontend/src/pages/SustainabilityPage.jsx` |

---

## 3. Calendar Sync

| Feature | Description | Key files |
|---|---|---|
| Google Calendar OAuth | Connect, sync, disconnect + revoke access. | `backend/calendar_sync/views.py` (GoogleConnectView, GoogleCallbackView, GoogleSyncView, GoogleDisconnectView); `google_calendar.py` |
| Google push webhook | Real-time event updates via Google webhook. | `backend/calendar_sync/views.py` (GoogleWebhookView) |
| Apple CalDAV | Connect with app-specific password, sync, disconnect. | `backend/calendar_sync/views.py` (AppleConnectView, AppleSyncView, AppleDisconnectView); `apple_calendar.py` |
| Outlook / Microsoft 365 | OAuth connect, sync, disconnect. | `backend/calendar_sync/views.py` (OutlookConnectView, OutlookCallbackView, OutlookSyncView, OutlookDisconnectView); `outlook_calendar.py` |
| Connection status | Unified status + last-sync view across all providers. | `backend/calendar_sync/views.py` (CalendarStatusView); `frontend/src/pages/ProfilePage.jsx` |

---

## 4. Itinerary & Trip Planning

| Feature | Description | Key files |
|---|---|---|
| Calendar events | CRUD for events with auto-classification (meeting, workout, travel, wedding, etc.) and formality inference. | `backend/itinerary/views.py` (CalendarEventViewSet); `models.py`; `backend/ritha/services/event_classifier.py`; `frontend/src/pages/ItineraryPage.jsx` |
| Unified calendar sync | One action syncs Google + Apple + Outlook and returns combined counts. | `backend/itinerary/views.py` (sync action); `frontend/src/pages/ItineraryPage.jsx` |
| Trips | Create/read/update/delete trips with destination, dates, notes. | `backend/itinerary/views.py` (TripViewSet); `frontend/src/pages/TripPlannerPage.jsx` |
| Packing checklist | Per-trip packing items linked to wardrobe or free-text, with packed state. | `backend/itinerary/views.py` (PackingChecklistViewSet); `models.py` (PackingChecklistItem); `frontend/src/pages/TripPlannerPage.jsx` |

---

## 5. AI Agents

All agents run through a common job model (`AgentJob`) with status tracking, input, output, and error capture.

| Agent | Description | Key files |
|---|---|---|
| Daily Look | Generates today's outfit from wardrobe given weather + calendar. | `backend/agents/services.py` (run_daily_look); `views.py` (DailyLookView); `frontend/src/pages/DashboardPage.jsx` |
| Packing List | 5-4-3-2-1 capsule-based packing list scaled by trip length + activities. | `backend/agents/services.py` (run_packing_list); `views.py` (PackingListView); `frontend/src/pages/TripPlannerPage.jsx` |
| Outfit Planner | Plans outfits for every day of a trip from calendar + weather + cultural rules. | `backend/agents/services.py` (run_outfit_planner); `views.py` (OutfitPlannerView) |
| Conflict Detector | Flags outfit / weather / schedule conflicts for a given date. | `backend/agents/services.py` (run_conflict_detector); `views.py` (ConflictDetectorView); `frontend/src/pages/ItineraryPage.jsx` |
| Cultural Advisor | Combines cultural DB + AI-generated destination-specific clothing advice, place/event highlights, wardrobe matches & gaps. | `backend/agents/services.py` (run_cultural_advisor); `views.py` (CulturalAdvisorView); `frontend/src/pages/CulturalPage.jsx` |
| Agent job history | Persists every run (pending/running/completed/failed) with I/O + errors. | `backend/agents/models.py` (AgentJob) |

---

## 6. Outfit Recommendations

| Feature | Description | Key files |
|---|---|---|
| Outfit CRUD | Recommendations with linked clothing items, weather snapshot, AI notes. | `backend/outfits/views.py` (OutfitRecommendationViewSet); `models.py` (OutfitRecommendation, OutfitItem) |
| Feedback | Accept / reject an outfit; used to train future recommendations. | `backend/outfits/views.py` (feedback action) |
| History | Past outfit recommendations with filtering. | `backend/outfits/views.py` (OutfitHistoryView) |

---

## 7. Cultural Guide

| Feature | Description | Key files |
|---|---|---|
| Cultural rules database | Curated etiquette rules (head / shoulders / knees, shoe removal, etc.) with info/warning/required severity per country/city/place. | `backend/cultural/models.py` (CulturalRule); `views.py` |
| Local events & festivals | Country/city events by month with clothing notes. | `backend/cultural/models.py` (LocalEvent); `views.py` |
| AI-enhanced advisor | Merges DB rules with LLM-generated advice, highlights, and shop-the-look gaps. | `backend/agents/services.py` (run_cultural_advisor) |
| Tabbed frontend UI | Etiquette / Places to Visit / Events / Your Wardrobe tabs. | `frontend/src/pages/CulturalPage.jsx` |

---

## 8. Sustainability

| Feature | Description | Key files |
|---|---|---|
| Sustainability logger | Log actions (wear again, carry-on only, weight saved, rental, secondhand) with CO₂ and points. | `backend/sustainability/models.py` (SustainabilityLog); `views.py` |
| User sustainability profile | Total points, total CO₂ saved, wear-again streak, tier (seedling/sapling/tree/forest). | `backend/sustainability/models.py` (UserSustainabilityProfile); `views.py` (SustainabilityTrackerView); `frontend/src/pages/SustainabilityPage.jsx` |
| Carry-on CO₂ estimator | Converts light-packing weight into CO₂ saved vs. checked bag. | `backend/wardrobe/views.py` (LuggageWeightView) |

---

## 9. Social & People

| Feature | Description | Key files |
|---|---|---|
| Social profile | Handle (@username), display name, bio, avatar, public vs. connections-only visibility. | `backend/social/models.py` (Profile); `views.py` (MyProfileView); `frontend/src/pages/PeoplePage.jsx` |
| Handle updates | Update handle with 30-day cooldown and lowercase normalization. | `backend/social/views.py` (UpdateHandleView) |
| User search | Find users by exact handle. | `backend/social/views.py` (UserSearchView) |
| Connection requests | Send / accept / reject / remove connection requests. | `backend/social/models.py` (Connection, ConnectionStatus); `views.py` |
| Block list | Block and unblock other users. | `backend/social/models.py` (BlockedUser); `views.py` (BlockListView, UnblockView) |

---

## 10. Messaging (1:1 Chat)

| Feature | Description | Key files |
|---|---|---|
| Conversations | Auto-created 1:1 conversations, normalized to prevent duplicates. | `backend/messaging/models.py` (Conversation); `views.py` (ConversationListView, ConversationOpenView) |
| Send / history | REST or WebSocket send, full history retrieval. | `backend/messaging/views.py` (SendMessageView, MessageListView); `frontend/src/pages/MessagesPage.jsx` |
| Read pointers | Per-user read timestamps and unread counts. | `backend/messaging/views.py` (MarkReadView) |
| Live WebSocket chat | Real-time delivery over `/ws/chat/<conversation_id>/`. | `backend/ritha/asgi.py`; `frontend/src/api/ws.js`, `pages/MessagesPage.jsx` |

---

## 11. Shared Wardrobes

| Feature | Description | Key files |
|---|---|---|
| Shared wardrobe CRUD | Collaborative wardrobes with owner/editor/viewer roles. | `backend/shared_wardrobe/models.py`, `views.py`; `frontend/src/pages/SharedWardrobesPage.jsx`, `SharedWardrobeDetailPage.jsx` |
| Membership management | Add / remove members with role assignment. | `backend/shared_wardrobe/views.py` (MemberAddView, MemberRemoveView) |
| Shared items | Add/remove items independent of personal wardrobes for privacy. | `backend/shared_wardrobe/models.py` (SharedWardrobeItem); `views.py` |
| Live updates | Real-time WebSocket updates when members or items change. | `backend/shared_wardrobe/consumers.py`, `routing.py`; `frontend/src/api/ws.js` |

---

## 12. Weather

| Feature | Description | Key files |
|---|---|---|
| Forecast by coords or location | Open-Meteo-backed weather with temperature, precipitation, wind, humidity, condition. | `backend/ritha/services/views.py` (WeatherView); `services/weather.py` |
| Weather snapshot on outfits | Weather is frozen into each outfit recommendation for context. | `backend/outfits/models.py` (OutfitRecommendation.weather_snapshot) |

---

## 13. Frontend Pages

| Page | Purpose | File |
|---|---|---|
| Dashboard | Today's weather, daily outfit, upcoming events, sustainability stats. | `frontend/src/pages/DashboardPage.jsx` |
| Wardrobe | Browse / filter / add / edit / delete items, photo-based AI add. | `frontend/src/pages/WardrobePage.jsx` |
| Itinerary | Calendar view, sync, add events, conflict check. | `frontend/src/pages/ItineraryPage.jsx` |
| Trip Planner | Trips, packing lists, outfit planning. | `frontend/src/pages/TripPlannerPage.jsx` |
| Cultural Guide | Tabbed etiquette / places / events / wardrobe view per destination. | `frontend/src/pages/CulturalPage.jsx` |
| Sustainability | Points, CO₂, streak, luggage weight calculator. | `frontend/src/pages/SustainabilityPage.jsx` |
| Profile | Account settings + calendar connections. | `frontend/src/pages/ProfilePage.jsx` |
| People | Handle/bio/visibility, find users, manage requests and blocks. | `frontend/src/pages/PeoplePage.jsx` |
| Messages | 1:1 chat with live updates. | `frontend/src/pages/MessagesPage.jsx` |
| Shared Wardrobes | List + detail views for collaborative wardrobes. | `frontend/src/pages/SharedWardrobesPage.jsx`, `SharedWardrobeDetailPage.jsx` |
| Login / Register | Email-based auth. | `frontend/src/pages/LoginPage.jsx`, `Register.jsx` |
| Verify / Forgot / Reset | Email verification and password recovery. | `frontend/src/pages/VerifyEmail.jsx`, `ForgotPassword.jsx`, `ResetPassword.jsx` |

---

## 14. System & Infrastructure

| Feature | Description | Key files |
|---|---|---|
| Health check | Liveness endpoint. | `backend/ritha/health.py` |
| OpenAPI / Swagger / ReDoc | Auto-generated API docs via drf-spectacular. | `backend/ritha/urls.py` |
| Runtime config endpoint | Exposes env-specific config to clients. | `backend/ritha/config_view.py` |
| JWT WebSocket auth | Token-authenticated Channels consumers. | `backend/ritha/ws_auth.py` |
| CORS / logging / exception middleware | Standard cross-cutting middleware. | `backend/ritha/middleware.py`, `exceptions.py` |
| Celery background tasks | Async queue for calendar sync, AI agents, email, etc. | `backend/ritha/celery.py`, `backend/agents/tasks.py` |
| Admin interfaces | Django admin registrations for all domain apps. | `backend/*/admin.py` |
| User data export | Management command to export a user's data (privacy / GDPR). | `backend/auth_app/management/commands/export_user_data.py` |

---

## 15. Data Model Summary

| App | Models |
|---|---|
| `auth_app` | User (custom: OAuth tokens, timezone, push tokens) |
| `wardrobe` | ClothingItem |
| `itinerary` | CalendarEvent, Trip, PackingChecklistItem |
| `cultural` | CulturalRule, LocalEvent |
| `sustainability` | SustainabilityLog, UserSustainabilityProfile |
| `outfits` | OutfitRecommendation, OutfitItem |
| `social` | Profile, Connection, BlockedUser |
| `messaging` | Conversation, Message |
| `shared_wardrobe` | SharedWardrobe, SharedWardrobeMember, SharedWardrobeItem |
| `agents` | AgentJob |

---

## 16. Integrations

- **Mistral AI** — image analysis, receipt parsing, outfit/cultural/packing agents
- **Open-Meteo** — weather forecasts (no API key required)
- **Google Calendar API** — OAuth sync + push webhooks
- **Microsoft Graph / Outlook** — OAuth calendar sync
- **Apple CalDAV** — calendar sync via app-specific passwords
- **Firebase Cloud Messaging** — device push notification token registration
- **Django Channels** — WebSockets for live chat and shared wardrobes
- **Celery** — background task queue
- **drf-spectacular** — OpenAPI schema + Swagger/ReDoc UIs
