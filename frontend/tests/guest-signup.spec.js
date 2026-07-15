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
  home: { city: 'Bengaluru', temp_c: 26, assumed: true },
  weather_gap: { home_city: 'Bengaluru', home_temp_c: 26, dest_temp_c: 8, delta_c: -18, colder: true, assumed_home: true, headline: "Your closet's built for 26°C. Tokyo isn't." },
  cues: [
    { icon: '🧥', text: 'You have no real cold-weather layers', tag: 'gap' },
    { icon: '👟', text: 'Shoes off indoors — temples & ryokan', tag: 'dress code' },
    { icon: '🌅', text: 'Layer up for chilly April mornings', tag: 'April tip' },
  ],
  packing: { piece_count: 6, line_count: 6, volume_l: 12.8, bag_capacity_l: 40, percent_of_bag: 52, note: '6 pieces travel fine · 12.8 L' },
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

  test('weather gap: headline, home-vs-dest delta, tagged cue cards (S3)', async ({ page }) => {
    await page.goto('/')
    await page.getByPlaceholder('e.g. Tokyo').fill('Tokyo, Japan')
    await page.getByLabel('Trip start date').fill('2027-04-06')
    await page.getByRole('button', { name: 'See my trip →' }).click()

    await expect(page.getByText("Tokyo isn't.")).toBeVisible()       // gap headline
    await expect(page.getByText('-18°')).toBeVisible()               // delta
    await expect(page.getByText('colder')).toBeVisible()
    await expect(page.getByText('You have no real cold-weather layers')).toBeVisible()
    await expect(page.getByText('gap', { exact: true })).toBeVisible()
    await expect(page.getByText('April tip')).toBeVisible()
  })

  test('packing gauge: pieces · liters · % of 40L + fill bar (S4)', async ({ page }) => {
    await page.goto('/')
    await page.getByPlaceholder('e.g. Tokyo').fill('Tokyo, Japan')
    await page.getByRole('button', { name: 'See my trip →' }).click()

    await expect(page.getByText('6 pieces travel fine · 12.8 L')).toBeVisible()
    await expect(page.getByText('52% of 40L')).toBeVisible()
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
    // Catch-all FIRST so any endpoint we don't explicitly mock returns an empty
    // paginated payload instead of hanging on the (absent) dev backend. Routes
    // registered later take precedence in Playwright, so the specific mocks and
    // mockAuthMe below win over this fallback.
    await page.route('**/api/**', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ results: [], count: 0 }) }),
    )

    // Simulate the post-signup state: authed + the guest stash still present.
    await injectAuth(page)
    await mockAuthMe(page)
    await page.route('**/api/itinerary/trips/', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ results: [] }) }),
    )
    await page.route('**/api/shared-wardrobes/', (route) =>
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) }),
    )
    await page.addInitScript(() => {
      localStorage.setItem('ritha_pending_trip', JSON.stringify({
        destination: 'Tokyo, Japan',
        place: { city: 'Tokyo', country: 'Japan', countryCode: 'JP' },
        date: '2027-04-06', endDate: '2027-04-12', gender: 'women',
      }))
    })

    await page.goto('/trips')

    // TripPlannerPage consumes the stash and opens the new-trip form pre-filled.
    // (App no longer fires a redundant same-path redirect that would remount and
    // drop the pre-fill — see AppRoutes' pending-trip effect.)
    // Wait for the form itself first for a clearer failure if it never renders.
    await expect(page.getByText('Plan a new trip')).toBeVisible()
    await expect(page.getByPlaceholder('e.g. Tokyo Adventure')).toHaveValue('Trip to Tokyo, Japan')
    const dateInputs = page.locator('input[type="date"]')
    await expect(dateInputs.nth(0)).toHaveValue('2027-04-06')   // start_date
    await expect(dateInputs.nth(1)).toHaveValue('2027-04-12')   // end_date (endDate carried through)
  })
})
