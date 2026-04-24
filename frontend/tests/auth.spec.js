import { test, expect } from '@playwright/test'
import { TEST_USER, TEST_TOKENS, mockAuthMe, mockAuthMeUnauthorized, injectAuth } from './fixtures/auth.js'
import { mockAllDashboardApis } from './fixtures/mocks.js'

test.describe('Login page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthMeUnauthorized(page)
  })

  test('shows login form by default', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible()
    await expect(page.getByPlaceholder('you@example.com')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Sign in' })).toBeVisible()
  })

  test('shows branding panel with Ritha name', async ({ page }) => {
    await page.goto('/login')
    await expect(page.getByText('Ritha')).toBeVisible()
    await expect(page.getByText('Your wardrobe assistant')).toBeVisible()
    await expect(page.getByText('Dress for your day.')).toBeVisible()
  })

  test('successful login redirects to dashboard', async ({ page }) => {
    await page.route('**/api/auth/login/', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ access: TEST_TOKENS.access, refresh: TEST_TOKENS.refresh }),
      })
    })
    await mockAuthMe(page)
    await mockAllDashboardApis(page)

    await page.goto('/login')
    await page.getByPlaceholder('you@example.com').fill('jane@example.com')
    await page.getByPlaceholder('••••••••').fill('password123')
    await page.getByRole('button', { name: 'Sign in' }).click()

    await expect(page).toHaveURL('/', { timeout: 10000 })
  })

  test('shows error on invalid credentials', async ({ page }) => {
    await page.route('**/api/auth/login/', (route) => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ error: { message: 'Invalid credentials.' } }),
      })
    })

    await page.goto('/login')
    await page.getByPlaceholder('you@example.com').fill('wrong@example.com')
    await page.getByPlaceholder('••••••••').fill('wrongpass')
    await page.getByRole('button', { name: 'Sign in' }).click()

    await expect(page.getByText('Invalid credentials.')).toBeVisible()
  })

  test('shows email not verified error', async ({ page }) => {
    await page.route('**/api/auth/login/', (route) => {
      route.fulfill({
        status: 403,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'email_not_verified', message: 'Email not verified' } }),
      })
    })

    await page.goto('/login')
    await page.getByPlaceholder('you@example.com').fill('jane@example.com')
    await page.getByPlaceholder('••••••••').fill('password123')
    await page.getByRole('button', { name: 'Sign in' }).click()

    await expect(page.getByText('Please verify your email')).toBeVisible()
  })

  test('shows loading state during submission', async ({ page }) => {
    await page.route('**/api/auth/login/', async (route) => {
      await new Promise(r => setTimeout(r, 500))
      route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ access: 'a', refresh: 'r' }) })
    })
    await mockAuthMe(page)

    await page.goto('/login')
    await page.getByPlaceholder('you@example.com').fill('jane@example.com')
    await page.getByPlaceholder('••••••••').fill('password123')
    await page.getByRole('button', { name: 'Sign in' }).click()

    await expect(page.getByText('Loading…')).toBeVisible()
  })

  test('forgot password link navigates correctly', async ({ page }) => {
    await page.goto('/login')
    await page.getByText('Forgot password?').click()
    await expect(page).toHaveURL('/forgot-password')
  })
})

test.describe('Registration', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthMeUnauthorized(page)
  })

  test('switches to register mode', async ({ page }) => {
    await page.goto('/login')
    await page.getByRole('button', { name: 'Sign up' }).click()

    await expect(page.getByRole('heading', { name: 'Create account' })).toBeVisible()
    await expect(page.getByPlaceholder('Jane')).toBeVisible()
  })

  test('successful registration redirects to verify email', async ({ page }) => {
    await page.route('**/api/auth/register/', (route) => {
      route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ id: 1, email: 'new@example.com' }),
      })
    })

    await page.goto('/login')
    await page.getByRole('button', { name: 'Sign up' }).click()
    await page.getByPlaceholder('Jane').fill('New')
    await page.getByPlaceholder('you@example.com').fill('new@example.com')
    await page.getByPlaceholder('Min. 8 characters').fill('newpassword123')
    await page.getByRole('button', { name: 'Create account' }).click()

    await expect(page).toHaveURL(/\/verify-email/)
  })

  test('shows validation error on register failure', async ({ page }) => {
    await page.route('**/api/auth/register/', (route) => {
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ error: { code: 'validation_error', detail: { email: 'A user with this email already exists.' } } }),
      })
    })

    await page.goto('/login')
    await page.getByRole('button', { name: 'Sign up' }).click()
    await page.getByPlaceholder('Jane').fill('Jane')
    await page.getByPlaceholder('you@example.com').fill('existing@example.com')
    await page.getByPlaceholder('Min. 8 characters').fill('password123')
    await page.getByRole('button', { name: 'Create account' }).click()

    await expect(page.getByText('A user with this email already exists.')).toBeVisible()
  })

  test('can switch back to login mode', async ({ page }) => {
    await page.goto('/login')
    await page.getByRole('button', { name: 'Sign up' }).click()
    await expect(page.getByRole('heading', { name: 'Create account' })).toBeVisible()

    await page.getByRole('button', { name: 'Sign in' }).click()
    await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible()
  })
})

test.describe('Forgot password', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthMeUnauthorized(page)
  })

  test('renders forgot password page', async ({ page }) => {
    await page.goto('/forgot-password')
    await expect(page.getByText('Reset your password')).toBeVisible()
    await expect(page.getByRole('button', { name: 'Send reset link' })).toBeVisible()
  })
})

test.describe('Auth redirects', () => {
  test('unauthenticated user is redirected to /login', async ({ page }) => {
    await mockAuthMeUnauthorized(page)
    await page.goto('/')
    await expect(page).toHaveURL('/login')
  })

  test('unauthenticated user visiting /wardrobe is redirected', async ({ page }) => {
    await mockAuthMeUnauthorized(page)
    await page.goto('/wardrobe')
    await expect(page).toHaveURL('/login')
  })

  test('authenticated user visiting /login is redirected to dashboard', async ({ page }) => {
    await injectAuth(page)
    await mockAuthMe(page)
    await page.goto('/login')
    await expect(page).toHaveURL('/')
  })

  test('authenticated user visiting /forgot-password is redirected', async ({ page }) => {
    await injectAuth(page)
    await mockAuthMe(page)
    await page.goto('/forgot-password')
    await expect(page).toHaveURL('/')
  })
})
