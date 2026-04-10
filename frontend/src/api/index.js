// src/api/index.js  — named exports for every backend endpoint

import { api } from './client.js'

// ── Auth ──────────────────────────────────────────────────────────────────
export const auth = {
  register:       (data) => api.post('/auth/register/', data),
  login:          (data) => api.post('/auth/login/', data),
  logout:         (refresh) => api.post('/auth/logout/', { refresh }),
  me:             ()     => api.get('/auth/me/'),
  updateMe:       (data) => api.patch('/auth/me/', data),
  changePassword: (data) => api.post('/auth/me/password/', data),
  deleteAccount:  ()     => api.delete('/auth/me/delete/'),
  forgotPassword: (data) => api.post('/auth/forgot-password/', data),
  resetPassword:  (data) => api.post('/auth/reset-password/', data),
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
  analyzeImage: (file) => {
    // NB: do not set Content-Type manually — axios fills in the multipart boundary.
    const fd = new FormData()
    fd.append('image', file)
    return api.post('/wardrobe/analyze-image/', fd)
  },
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
  dailyLook:        (data) => api.post('/agents/daily-look/', data),
  packingList:      (data) => api.post('/agents/packing-list/', data),
  outfitPlanner:    (data) => api.post('/agents/outfit-planner/', data),
  conflictDetector: (data) => api.post('/agents/conflict-detector/', data),
  culturalAdvisor:  (data) => api.post('/agents/cultural-advisor/', data),
  smartRecommend:   (data) => api.post('/agents/smart-recommend/', data),
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
  status: () => api.get('/calendar/status/'),
  google: {
    connect: () => api.get('/calendar/google/connect/'),
    sync: () => api.post('/calendar/google/sync/'),
    disconnect: () => api.post('/calendar/google/disconnect/'),
  },
  apple: {
    connect: (data) => api.post('/calendar/apple/connect/', data),
    sync: () => api.post('/calendar/apple/sync/'),
    disconnect: () => api.post('/calendar/apple/disconnect/'),
  },
  outlook: {
    connect: () => api.get('/calendar/outlook/connect/'),
    sync: () => api.post('/calendar/outlook/sync/'),
    disconnect: () => api.post('/calendar/outlook/disconnect/'),
  },
}

// ── Social (profiles, search, connections) ───────────────────────────────
export const social = {
  profile: {
    get:          ()            => api.get('/social/me/profile/'),
    update:       (data)        => api.patch('/social/me/profile/', data),
    updateHandle: (handle)      => api.post('/social/me/profile/handle/', { handle }),
  },
  users: {
    search: (handle) => api.get(`/social/users/search/?handle=${encodeURIComponent(handle)}`),
  },
  connections: {
    list:    (status = '')   => api.get(`/social/connections/${status ? '?status=' + status : ''}`),
    request: (handle)        => api.post('/social/connections/request/', { handle }),
    accept:  (id)            => api.post(`/social/connections/${id}/accept/`),
    reject:  (id)            => api.post(`/social/connections/${id}/reject/`),
    remove:  (id)            => api.delete(`/social/connections/${id}/`),
  },
  blocks: {
    list:    ()       => api.get('/social/blocks/'),
    add:     (handle) => api.post('/social/blocks/', { handle }),
    remove:  (id)     => api.delete(`/social/blocks/${id}/`),
  },
}

// ── Messaging (1:1 chat) ─────────────────────────────────────────────────
export const messaging = {
  conversations: {
    list:     ()                       => api.get('/messages/conversations/'),
    openWith: (user_id)                => api.post('/messages/conversations/open/', { user_id }),
    messages: (id, before_id)          => api.get(`/messages/conversations/${id}/messages/${before_id ? '?before_id=' + before_id : ''}`),
    send:     (id, body)               => api.post(`/messages/conversations/${id}/send/`, { body }),
    markRead: (id)                     => api.post(`/messages/conversations/${id}/mark_read/`),
  },
}

// ── Shared wardrobes ─────────────────────────────────────────────────────
export const sharedWardrobes = {
  list:   ()            => api.get('/shared-wardrobes/'),
  create: (data)        => api.post('/shared-wardrobes/', data),
  get:    (id)          => api.get(`/shared-wardrobes/${id}/`),
  delete: (id)          => api.delete(`/shared-wardrobes/${id}/`),
  members: {
    add:    (id, user_id)        => api.post(`/shared-wardrobes/${id}/members/`, { user_id }),
    remove: (id, user_id)        => api.delete(`/shared-wardrobes/${id}/members/${user_id}/`),
  },
  items: {
    list:   (id)                 => api.get(`/shared-wardrobes/${id}/items/`),
    add:    (id, data)           => api.post(`/shared-wardrobes/${id}/items/`, data),
    delete: (id, item_id)        => api.delete(`/shared-wardrobes/${id}/items/${item_id}/`),
  },
}

// ── Health ────────────────────────────────────────────────────────────────
export const health = {
  check: () => api.get('/health/'),
}
