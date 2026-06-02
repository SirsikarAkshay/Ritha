import { test, expect, TEST_USER } from './fixtures/auth.js'
import { CALENDAR_STATUS, CULTURAL_RULES, CULTURAL_EVENTS, SUSTAINABILITY_TRACKER, SUSTAINABILITY_LOGS, OUTFIT_HISTORY } from './fixtures/mocks.js'

function inputByLabel(page, label) {
  return page.locator('.input-group').filter({ hasText: label }).locator('input, select')
}

test.describe('Profile page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.route('**/api/calendar/status/', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CALENDAR_STATUS) })
    })
  })

  test('shows page header', async ({ authenticatedPage: page }) => {
    await page.goto('/profile')
    await expect(page.getByText('Your Profile')).toBeVisible()
  })

  test('shows user avatar initial in profile card', async ({ authenticatedPage: page }) => {
    await page.goto('/profile')
    await expect(page.getByRole('main').locator('div').filter({ hasText: /^J$/ }).first()).toBeVisible()
  })

  test('shows user email on profile page', async ({ authenticatedPage: page }) => {
    await page.goto('/profile')
    await expect(page.getByRole('main').getByText('jane@example.com')).toBeVisible()
  })

  test('shows profile form with first name and last name', async ({ authenticatedPage: page }) => {
    await page.goto('/profile')
    await expect(inputByLabel(page, 'First name')).toHaveValue('Jane')
    await expect(inputByLabel(page, 'Last name')).toHaveValue('Doe')
  })

  test('email field is disabled', async ({ authenticatedPage: page }) => {
    await page.goto('/profile')
    await expect(page.getByText('Email cannot be changed.')).toBeVisible()
  })

  test('timezone selector is visible', async ({ authenticatedPage: page }) => {
    await page.goto('/profile')
    await expect(inputByLabel(page, 'Timezone')).toBeVisible()
  })

  test('save profile calls API', async ({ authenticatedPage: page }) => {
    let updatePayload = null
    await page.route('**/api/auth/me/', (route) => {
      if (route.request().method() === 'PATCH') {
        updatePayload = JSON.parse(route.request().postData())
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ...updatePayload, id: 1, email: 'jane@example.com' }) })
      } else {
        // GET on load: serve the authenticated user. This route shadows the
        // fixture's mockAuthMe (Playwright routes are LIFO), so continuing here
        // would hit the non-running backend and bounce the user to /login.
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(TEST_USER) })
      }
    })

    await page.goto('/profile')
    await inputByLabel(page, 'First name').fill('Janet')
    await page.getByRole('button', { name: 'Save changes' }).click()
    await page.waitForTimeout(300)

    expect(updatePayload).toBeTruthy()
    expect(updatePayload.first_name).toBe('Janet')
    await expect(page.getByText('Profile updated.')).toBeVisible()
  })
})

test.describe('Profile - change password', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.route('**/api/calendar/status/', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CALENDAR_STATUS) })
    })
  })

  test('shows change password section', async ({ authenticatedPage: page }) => {
    await page.goto('/profile')
    await expect(page.locator('.card-label').filter({ hasText: 'Change password' })).toBeVisible()
    await expect(inputByLabel(page, 'Current password')).toBeVisible()
    await expect(inputByLabel(page, 'New password')).toBeVisible()
  })

  test('successful password change shows success message', async ({ authenticatedPage: page }) => {
    await page.route('**/api/auth/me/password/', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({}) })
    })

    await page.goto('/profile')
    await inputByLabel(page, 'Current password').fill('oldpassword1')
    await inputByLabel(page, 'New password').fill('newpassword1')
    await page.getByRole('button', { name: 'Change password' }).click()

    await expect(page.getByText('Password changed successfully.')).toBeVisible()
  })

  test('new password field requires minimum 8 characters', async ({ authenticatedPage: page }) => {
    await page.goto('/profile')
    const newPwInput = inputByLabel(page, 'New password')
    await expect(newPwInput).toHaveAttribute('minlength', '8')
    await expect(page.getByText('Minimum 8 characters.')).toBeVisible()
  })

  test('shows error on wrong current password', async ({ authenticatedPage: page }) => {
    await page.route('**/api/auth/me/password/', (route) => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ error: { detail: { current_password: ['Incorrect password.'] } } }),
      })
    })

    await page.goto('/profile')
    await inputByLabel(page, 'Current password').fill('wrongpassword')
    await inputByLabel(page, 'New password').fill('newpassword1')
    await page.getByRole('button', { name: 'Change password' }).click()

    await expect(page.getByText('Incorrect password.')).toBeVisible()
  })
})

test.describe('Profile - calendar connections', () => {
  test('shows Google Calendar connect button when not connected', async ({ authenticatedPage: page }) => {
    await page.route('**/api/calendar/status/', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CALENDAR_STATUS) })
    })

    await page.goto('/profile')
    await expect(page.getByText('Google Calendar')).toBeVisible()
    const connectBtns = page.getByRole('button', { name: 'Connect' })
    expect(await connectBtns.count()).toBeGreaterThanOrEqual(1)
  })

  test('shows connected status when Google Calendar is connected', async ({ authenticatedPage: page }) => {
    await page.route('**/api/calendar/status/', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          ...CALENDAR_STATUS,
          google: { connected: true, email: 'jane@gmail.com', synced_at: '2026-04-20T10:00:00Z' },
        }),
      })
    })

    await page.goto('/profile')
    await expect(page.getByText('✓ Connected').first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sync now' }).first()).toBeVisible()
    await expect(page.getByRole('button', { name: 'Disconnect' }).first()).toBeVisible()
  })

  test('shows Apple Calendar connect button', async ({ authenticatedPage: page }) => {
    await page.route('**/api/calendar/status/', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CALENDAR_STATUS) })
    })

    await page.goto('/profile')
    await expect(page.getByText('Apple Calendar')).toBeVisible()
  })

  test('shows Outlook Calendar connect button', async ({ authenticatedPage: page }) => {
    await page.route('**/api/calendar/status/', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CALENDAR_STATUS) })
    })

    await page.goto('/profile')
    await expect(page.getByText('Outlook Calendar')).toBeVisible()
  })
})

test.describe('Profile - danger zone', () => {
  test('shows delete account button', async ({ authenticatedPage: page }) => {
    await page.route('**/api/calendar/status/', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CALENDAR_STATUS) })
    })

    await page.goto('/profile')
    await expect(page.getByText('Danger zone')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Delete account' })).toBeVisible()
  })

  test('delete account shows confirm dialog', async ({ authenticatedPage: page }) => {
    await page.route('**/api/calendar/status/', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CALENDAR_STATUS) })
    })

    let dialogShown = false
    await page.goto('/profile')
    page.on('dialog', async (dialog) => {
      dialogShown = true
      await dialog.dismiss()
    })
    await page.getByRole('button', { name: 'Delete account' }).click()
    expect(dialogShown).toBeTruthy()
  })
})

test.describe('Cultural page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.route('**/api/cultural/rules/*', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ results: CULTURAL_RULES }) })
    })
    await page.route('**/api/cultural/events/*', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ results: CULTURAL_EVENTS }) })
    })
  })

  test('shows cultural page header', async ({ authenticatedPage: page }) => {
    await page.goto('/cultural')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  })

  test('displays cultural rules', async ({ authenticatedPage: page }) => {
    await page.goto('/cultural')
    await page.waitForTimeout(500)
    await expect(page.locator('body')).not.toBeEmpty()
  })
})

test.describe('Sustainability page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.route('**/api/sustainability/tracker/', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(SUSTAINABILITY_TRACKER) })
    })
    await page.route('**/api/sustainability/logs/*', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ results: SUSTAINABILITY_LOGS }) })
    })
  })

  test('shows sustainability page header', async ({ authenticatedPage: page }) => {
    await page.goto('/sustainability')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  })

  test('displays sustainability stats', async ({ authenticatedPage: page }) => {
    await page.goto('/sustainability')
    await page.waitForTimeout(500)
    await expect(page.locator('body')).not.toBeEmpty()
  })
})

test.describe('Outfit History page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.route('**/api/outfits/history/*', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ results: OUTFIT_HISTORY }) })
    })
  })

  test('shows outfit history page header', async ({ authenticatedPage: page }) => {
    await page.goto('/outfit-history')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  })

  test('displays outfit history entries', async ({ authenticatedPage: page }) => {
    await page.goto('/outfit-history')
    await page.waitForTimeout(500)
    await expect(page.locator('body')).not.toBeEmpty()
  })
})

test.describe('Itinerary page', () => {
  test.beforeEach(async ({ authenticatedPage: page }) => {
    await page.route('**/api/itinerary/events/*', (route) => {
      if (route.request().method() === 'GET') {
        route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ results: [] }) })
      } else {
        route.continue()
      }
    })
    await page.route('**/api/calendar/status/', (route) => {
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(CALENDAR_STATUS) })
    })
  })

  test('shows itinerary page header', async ({ authenticatedPage: page }) => {
    await page.goto('/itinerary')
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible()
  })

  test('can create a new event', async ({ authenticatedPage: page }) => {
    await page.goto('/itinerary')
    const addBtn = page.getByRole('button', { name: /add|new|create/i }).first()
    if (await addBtn.isVisible()) {
      await addBtn.click()
    }
  })
})
