# Ritha Frontend

React 18 + Vite web app for the Ritha AI style companion.

## Tech stack
- **React 18** with hooks
- **React Router 6** for navigation  
- **Axios** with auto token refresh
- **Vite** with hot reload and proxy to Django backend
- **DM Serif Display + DM Sans** typography
- **CSS Modules** for component styles, global design tokens in `styles/globals.css`

## Quick start

```bash
# Install
npm install

# Dev server (proxies /api to localhost:8000)
npm run dev

# Production build
npm run build
```

The backend (Django) must be running on `localhost:8000`. Start it with:
```bash
cd ../         # back to backend directory
python manage.py runserver
```

Then open **http://localhost:3000**

## Pages

| Route | Page | Description |
|-------|------|-------------|
| `/` | Dashboard | Today's outfit, weather, schedule, generate look |
| `/wardrobe` | Wardrobe | Browse, search, filter, add clothing items |
| `/itinerary` | Schedule | Calendar events, add/delete, conflict detection |
| `/trips` | Trips | Trip management, AI per-day outfit planning |
| `/cultural` | Culture | Destination etiquette rules, local events |
| `/sustainability` | Impact | CO₂ tracker, eco points, luggage weight calc |
| `/profile` | Profile | Account settings, password change |
| `/login` | Auth | Login + register (single page, tab switch) |

## Environment / proxy

The `vite.config.js` proxies all `/api/*` requests to `http://localhost:8000`, so no CORS issues in development. In production, configure your reverse proxy (nginx, Caddy) to route `/api` to the Django container.

## Design system

All design tokens are in `src/styles/globals.css`. Key variables:

```css
--midnight     /* page background */
--surface-1    /* card background */
--surface-2    /* secondary surface */
--terra        /* primary accent (warm terracotta) */
--sage         /* success / eco */
--sky          /* info / links */
--gold         /* warnings */
--cream        /* primary text */
--cream-dim    /* secondary text */
--font-display /* DM Serif Display — headings */
--font-body    /* DM Sans — body text */
```

## Structure

```
src/
├── api/
│   ├── client.js          # Axios instance, token management, data unwrapping
│   └── index.js           # Named exports for every backend endpoint
├── components/
│   ├── Layout.jsx          # Sidebar + mobile nav shell
│   └── Toast.jsx           # Notification toasts
├── hooks/
│   ├── useAuth.jsx         # Auth context: login, logout, user state
│   └── useToast.jsx        # Toast state management
├── pages/
│   ├── DashboardPage.jsx
│   ├── WardrobePage.jsx
│   ├── ItineraryPage.jsx
│   ├── TripPlannerPage.jsx
│   ├── CulturalPage.jsx
│   ├── SustainabilityPage.jsx
│   ├── ProfilePage.jsx
│   └── LoginPage.jsx
├── styles/
│   └── globals.css         # Design system, layout, components
└── App.jsx                 # Router + auth provider + toast root
```
