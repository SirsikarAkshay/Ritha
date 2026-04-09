// src/api/index.js  — named exports for every backend endpoint

import { api } from './client.js'

// ── Auth ──────────────────────────────────────────────────────────────────
export const auth = {
  register: (data)  => api.post('/auth/register/', data),
  login:    (data)  => api.post('/auth/login/', data),
  logout:   (refresh) => api.post('/auth/logout/', { refresh }),
  me:             ()     => api.get('/auth/me/'),
  updateMe:       (data) => api.patch('/auth/me/', data),
  changePassword:       (data) => api.post('/auth/me/password/', data),
  deleteAccount:        ()     => api.delete('/auth/me/delete/'),
  registerPushToken:    (data) => api.post('/auth/push-token/', data),
  verifyEmail:          (data) => api.post('/auth/verify-email/', data),
  resendVerification:   (data) => api.post('/auth/resend-verification/', data),
  forgotPassword:       (data) => api.post('/auth/forgot-password/', data),
  resetPassword:        (data) => api.post('/auth/reset-password/', data),
}

// ── Wardrobe ──────────────────────────────────────────────────────────────
export const wardrobe = {
  list:   (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return api.get(`/wardrobe/items/${q ? '?' + q : ''}`)
  },
  get:    (id)   => api.get(`/wardrobe/items/${id}/`),
  create: (data) => api.post('/wardrobe/items/', data),
  update: (id, data) => api.patch(`/wardrobe/items/${id}/`, data),
  delete: (id)   => api.delete(`/wardrobe/items/${id}/`),
  luggageWeight: (item_ids, airline = 'default') =>
    api.post('/wardrobe/luggage-weight/', { item_ids, airline }),
}

// ── Itinerary ─────────────────────────────────────────────────────────────
export const itinerary = {
  events: {
    list:   (params = {}) => {
      const q = new URLSearchParams(params).toString()
      return api.get(`/itinerary/events/${q ? '?' + q : ''}`)
    },
    create: (data) => api.post('/itinerary/events/', data),
    update: (id, data) => api.patch(`/itinerary/events/${id}/`, data),
    delete: (id)   => api.delete(`/itinerary/events/${id}/`),
    sync:   ()     => api.post('/itinerary/events/sync/'),
  },
  trips: {
    list:   ()     => api.get('/itinerary/trips/'),
    create: (data) => api.post('/itinerary/trips/', data),
    delete: (id)   => api.delete(`/itinerary/trips/${id}/`),
  },
}

// ── Outfits ───────────────────────────────────────────────────────────────
export const outfits = {
  daily:    (date) => api.get(`/outfits/recommendations/daily/${date ? '?date=' + date : ''}`),
  list:     (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return api.get(`/outfits/recommendations/${q ? '?' + q : ''}`)
  },
  feedback: (id, accepted) =>
    api.patch(`/outfits/recommendations/${id}/feedback/`, { accepted }),
}

// ── Agents ────────────────────────────────────────────────────────────────
export const agents = {
  dailyLook:       (data) => api.post('/agents/daily-look/', data),
  packingList:     (data) => api.post('/agents/packing-list/', data),
  outfitPlanner:   (data) => api.post('/agents/outfit-planner/', data),
  conflictDetector:(data) => api.post('/agents/conflict-detector/', data),
  culturalAdvisor: (data) => api.post('/agents/cultural-advisor/', data),
}

// ── Weather ───────────────────────────────────────────────────────────────
export const weather = {
  byLocation: (location, date) => {
    const params = new URLSearchParams({ location })
    if (date) params.set('date', date)
    return api.get(`/weather/?${params}`)
  },
  byCoords: (lat, lon) => api.get(`/weather/?lat=${lat}&lon=${lon}`),
}

// ── Cultural ──────────────────────────────────────────────────────────────
export const cultural = {
  rules:  (country, city) => {
    const params = new URLSearchParams({ ...(country && { country }), ...(city && { city }) })
    return api.get(`/cultural/rules/?${params}`)
  },
  events: (country, month) => {
    const params = new URLSearchParams({ ...(country && { country }), ...(month && { month }) })
    return api.get(`/cultural/events/?${params}`)
  },
}

// ── Sustainability ────────────────────────────────────────────────────────
export const sustainability = {
  tracker: ()     => api.get('/sustainability/tracker/'),
  logs:    (action) => api.get(`/sustainability/logs/${action ? '?action=' + action : ''}`),
}


// ── Calendar ──────────────────────────────────────────────────────────────
export const calendar = {
  status:            ()     => api.get('/calendar/status/'),
  googleConnectUrl:  ()     => api.get('/calendar/google/connect/'),
  googleSync:        ()     => api.post('/calendar/google/sync/'),
  googleDisconnect:  ()     => api.post('/calendar/google/disconnect/'),
  appleConnect:      (data) => api.post('/calendar/apple/connect/', data),
  appleSync:         ()     => api.post('/calendar/apple/sync/'),
  appleDisconnect:   ()     => api.post('/calendar/apple/disconnect/'),
  outlookConnectUrl: ()     => api.get('/calendar/outlook/connect/'),
  outlookSync:       ()     => api.post('/calendar/outlook/sync/'),
  outlookDisconnect: ()     => api.post('/calendar/outlook/disconnect/'),
}

// ── Health ────────────────────────────────────────────────────────────────
export const health = {
  check: () => api.get('/health/'),
}
