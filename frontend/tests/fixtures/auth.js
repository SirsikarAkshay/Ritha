// Shared auth fixtures and API mock helpers for Playwright tests
import { test as base } from '@playwright/test'

export const TEST_USER = {
  id: 1,
  email: 'jane@example.com',
  first_name: 'Jane',
  last_name: 'Doe',
  timezone: 'Europe/Zurich',
  created_at: '2025-01-15T10:00:00Z',
  has_completed_onboarding: true,  // skip the /onboarding redirect in ProtectedRoute
}

export const TEST_TOKENS = {
  access: 'test-access-token-abc123',
  refresh: 'test-refresh-token-xyz789',
}

export function mockAuthMe(page, user = TEST_USER) {
  return page.route('**/api/auth/me/', (route) => {
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(user) })
  })
}

export function mockAuthMeUnauthorized(page) {
  return page.route('**/api/auth/me/', (route) => {
    route.fulfill({ status: 401, contentType: 'application/json', body: JSON.stringify({ error: { message: 'Not authenticated' } }) })
  })
}

export async function injectAuth(page) {
  await page.addInitScript((tokens) => {
    localStorage.setItem('gg_access', tokens.access)
    localStorage.setItem('gg_refresh', tokens.refresh)
  }, TEST_TOKENS)
}

export const test = base.extend({
  authenticatedPage: async ({ page }, use) => {
    await injectAuth(page)
    await mockAuthMe(page)
    await use(page)
  },
})

export { expect } from '@playwright/test'
