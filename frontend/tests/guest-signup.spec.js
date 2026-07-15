// Guest → signup → trip end-to-end.
// Covers the destination-first walkthrough: preview as a guest → "See my trip"
// → "Keep this trip" save modal → "Save my trip" deep-links into register mode
// (the /register-route fix) → previewed trip (incl. the end date) pre-fills /trips.
//
// Runs against `npm run dev` (see playwright.config.js). All network is mocked
// via page.route, so no backend is required — same pattern as the other specs.
import { test, expect } from '@playwright/test'
import { injectAuth, mockAuthMe } from './fixtures/auth.js'

// Canned public-insights payload (backend normally fills this from Open-Meteo +
// Mistral; mocked here so the flow is deterministic and offline).
const INSIGHTS = {
  weather: { temp_c: 8, feels_like_c: 6, condition: 'Cold & clear', is_cold: true, is_raining: false, is_hot: false },
  dress_code: ['Shoes off indoors — temples & ryokan', 'Cover shoulders at shrines'],
  capsule_note: "Based on a standard capsule for Tokyo's cold weather — personalise it in one tap.",
  capsule: [
    { name: 'Formal Shirt', category: 'top' },
    { name: 'Cotton T-shirt', category: 'top' },
    { name: 'Indigo Jeans', category: 'bottom' },
    { name: 'White Sneakers', category: 'footwear' },
  ],
  gaps: [
    { name: 'Merino sweater', why: 'The warm mid-layer your closet has zero of.' },
    { name: 'Wool overcoat', why: 'A real coat for 8°C evenings.' },
    { name: 'Knit scarf', why: 'Makes cotton work in the cold.' },
    { name: 'Thermal base layer', why: 'For chilly hanami mornings.' },
  ],
  places: [{ name: 'Ueno Park' }, { name: 'Meiji Shrine' }, { name: 'Sensō-ji' }],
}

function mockGuestApis(page) {
  return Promise.all([
    page.route('**/api/agents/trip-insights/', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ output: INSIGHTS }) })
    }),
    page.route('https://geocoding-api.open-meteo.com/**', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ results: [{ name: 'Tokyo', country: 'Japan', country_code: 'JP', latitude: 35.68, longitude: 139.69 }] }) })
    }),
  ])
}

test.describe('Guest destination-first preview (Scenes 1–4)', () => {
  test.beforeEach(async ({ page }) => { await mockGuestApis(page) })

  test('hook copy: tagline, "Where are you going?", 3-step flag, new sub', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByText('Ritha · Your travel stylist')).toBeVisible()
    await expect(page.getByRole('heading', { name: /Where are you going\?/ })).toBeVisible()
    await expect(page.getByText('No sign-up. No closet setup.')).toBeVisible()
    await expect(page.getByText(/See it/)).toBeVisible()
    await expect(page.getByText(/Pack it together/)).toBeVisible()
  })

  test('form: date-range inputs, travelling-with, crew soft-prompt, CTA label', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByLabel('Trip start date')).toBeVisible()
    await expect(page.getByLabel('Trip end date')).toBeVisible()
    await expect(page.getByText('Just me')).toBeVisible()
    await expect(page.getByRole('button', { name: 'See my trip →' })).toBeVisible()

    await page.getByRole('button', { name: /Add friends/ }).click()
    await expect(page.getByText(/once your trip's created/)).toBeVisible()
    await expect(page.getByText(/hit.*See my trip.*first/i)).toBeVisible()
  })

  test('See my trip → insight preview: gap teaser + reassurance + save nudge', async ({ page }) => {
    await page.goto('/')
    await page.getByPlaceholder('e.g. Tokyo').fill('Tokyo, Japan')
    await page.getByLabel('Trip start date').fill('2027-04-06')
    await page.getByLabel('Trip end date').fill('2027-04-12')
    await page.getByRole('button', { name: 'See my trip →' }).click()

    await expect(page.getByText(/pieces? your closet's missing/)).toBeVisible()
    await expect(page.getByText('not a guess about you')).toBeVisible()
    await expect(page.getByText('Like what you see? Save this trip to make it yours.')).toBeVisible()
  })
})

test.describe('Save trigger → register (Scene 5 + /register fix)', () => {
  test.beforeEach(async ({ page }) => { await mockGuestApis(page) })

  async function previewToModal(page) {
    await page.goto('/')
    await page.getByPlaceholder('e.g. Tokyo').fill('Tokyo, Japan')
    await page.getByLabel('Trip start date').fill('2027-04-06')
    await page.getByLabel('Trip end date').fill('2027-04-12')
    await page.getByRole('button', { name: 'See my trip →' }).click()
    await page.getByRole('button', { name: /Save this trip/ }).click()
  }

  test('save modal: "Keep this trip" + fineprint; stash carries the end date', async ({ page }) => {
    await previewToModal(page)
    await expect(page.getByRole('heading', { name: 'Keep this trip' })).toBeVisible()
    await expect(page.getByText(/attaches automatically/)).toBeVisible()
    await expect(page.getByText(/no card/)).toBeVisible()

    const pending = await page.evaluate(() => JSON.parse(localStorage.getItem('ritha_pending_trip') || '{}'))
    expect(pending.date).toBe('2027-04-06')
    expect(pending.endDate).toBe('2027-04-12')
  })

  test('"Save my trip" deep-links to /login?mode=register and shows the register form', async ({ page }) => {
    await previewToModal(page)
    await page.getByRole('button', { name: 'Save my trip' }).click()

    await expect(page).toHaveURL(/\/login\?mode=register/)
    await expect(page.getByRole('heading', { name: 'Create account' })).toBeVisible()
    await expect(page.getByText('First name')).toBeVisible()
  })
})

test.describe('Register-mode deep link (LoginPage ?mode= param)', () => {
  test('/login?mode=register opens in register mode', async ({ page }) => {
    await page.goto('/login?mode=register')
    await expect(page.getByRole('heading', { name: 'Create account' })).toBeVisible()
    await expect(page.getByText('First name')).toBeVisible()
  })

  test('/login (no param) stays in login mode', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible()
    await expect(page.getByText('First name')).toHaveCount(0)
  })
})

test.describe('Previewed trip attaches after signup (Scene 5 → /trips prefill)', () => {
  test('/trips pre-fills the previewed destination + start/end dates', async ({ page }) => {
    // Simulate the post-signup state: authed + the guest stash still present.
    await injectAuth(page)
    await mockAuthMe(page)
    await page.addInitScript(() => {
      localStorage.setItem('ritha_pending_trip', JSON.stringify({
        destination: 'Tokyo, Japan',
        place: { city: 'Tokyo', country: 'Japan', countryCode: 'JP' },
        date: '2027-04-06', endDate: '2027-04-12', gender: 'women',
      }))
    })
    await page.route('**/api/itinerary/trips/', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ results: [] }) })
    })
    await page.route('**/api/shared-wardrobes/', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
    })

    await page.goto('/trips')

    // TripPlannerPage consumes the stash, opens the new-trip form pre-filled.
    await expect(page.getByDisplayValue('Trip to Tokyo, Japan')).toBeVisible()
    await expect(page.getByDisplayValue('2027-04-06')).toBeVisible()   // start_date
    await expect(page.getByDisplayValue('2027-04-12')).toBeVisible()   // end_date (endDate carried through)
  })
})
