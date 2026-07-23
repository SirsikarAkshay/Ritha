# Social Login Setup — Google & Apple (Ritha)

How "Sign in with Google" and "Sign in with Apple" are wired, and the provider
setup + env vars needed to turn them on. Web only for now; native mobile is a
later phase (see the bottom).

**Legend:** ⚙ you do it (console/env) · 🤖 already in the code

---

## How it works

Both providers use the same shape: the browser gets a signed **ID token** from
the provider's SDK, POSTs it to our backend, and we verify it and mint our own
JWT. No server-side OAuth redirect flow, and **no client secret / `.p8` key** —
we only verify the ID token's signature, we never call the provider's token
endpoint.

```
Browser ──(Google/Apple SDK)──▶ ID token
   │
   └──POST /api/auth/social/{google,apple}/──▶ backend
                                                  │ verify signature + aud + iss
                                                  │ find-or-create user (email-verified)
                                                  ◀── { access, refresh, created }
   │
   └── store tokens (gg_access / gg_refresh) exactly like a password login
```

- 🤖 **Endpoints:** `POST /api/auth/social/google/` (body `{credential}` — GSI's
  field — or `{id_token}`) and `POST /api/auth/social/apple/` (body
  `{id_token, first_name?, last_name?}`). Both return `{access, refresh, created}`.
- 🤖 **Verification:** Google via the `google-auth` lib against `GOOGLE_CLIENT_ID`;
  Apple via `PyJWT`'s JWKS client against the `APPLE_CLIENT_ID` allowlist and
  `iss = https://appleid.apple.com`.
- 🤖 **Buttons render only when configured** — each is gated on its `VITE_*` build
  var, so nothing appears (and nothing breaks) until you set them.

### Account behavior

- **Linking by verified email:** if someone signed up with email+password and
  later uses Google/Apple on the *same* address, they're logged into the **same
  account** (providers verify the email for us). No duplicate accounts.
- **Apple "Hide My Email":** returning users who stop sending an email are matched
  by their stable Apple `sub` instead.
- **Social-only accounts** get an unusable password (password login just fails
  for them) and `is_email_verified = True` — they skip the email-verification
  gate entirely. `auth_provider` records how the account was created.

---

## Environment variables

| Var | Where | Value | Notes |
|---|---|---|---|
| `GOOGLE_CLIENT_ID` | backend | Google OAuth **Web** client ID | Reuse the existing Calendar OAuth client. Already set if Calendar works. |
| `VITE_GOOGLE_CLIENT_ID` | frontend build | same as above | Baked at build time (like `VITE_API_BASE_URL`). |
| `APPLE_CLIENT_ID` | backend | Apple **Services ID** (e.g. `com.getritha.web`) | Comma-separated allowlist — add a native bundle ID here later. |
| `VITE_APPLE_CLIENT_ID` | frontend build | same Services ID | |
| `VITE_APPLE_REDIRECT_URI` | frontend build | your registered **https** return URL | e.g. `https://ritha-web.onrender.com/login` |

Client IDs are **not secret** — safe to expose in the frontend bundle.

---

## Google setup ⚙

Google needs ~15 minutes and no new project — reuse the Cloud project that
already backs Calendar OAuth.

1. **Google Cloud Console → APIs & Services → Credentials →** open your existing
   **OAuth 2.0 Web client** (the one in `GOOGLE_CLIENT_ID`).
2. Under **Authorized JavaScript origins**, add every origin the login page is
   served from:
   - `https://ritha-web.onrender.com` (and your custom domain, e.g. `https://getritha.com`)
   - `http://localhost:5175` for local dev
   > JavaScript origins are **separate** from the Authorized *redirect URIs*
   > Calendar uses — Google Identity Services checks origins, not redirects.
3. Set `GOOGLE_CLIENT_ID` (backend) and `VITE_GOOGLE_CLIENT_ID` (frontend build)
   to that client ID, then rebuild/redeploy the frontend.

That's it — the "Continue with Google" button appears and works, including on
localhost.

---

## Apple setup ⚙

Apple is heavier: it needs a paid Developer account and domain verification, but
because we verify the ID token directly you can **skip the `.p8` key / client
secret**.

1. **Enroll in the Apple Developer Program** ($99/yr).
2. **Certificates, Identifiers & Profiles → Identifiers → App ID:** create one (or
   reuse the app's) and enable the **Sign in with Apple** capability.
3. **Identifiers → Services IDs:** create a Services ID (e.g. `com.getritha.web`)
   — this is your `APPLE_CLIENT_ID`. Enable **Sign in with Apple** on it and click
   **Configure**:
   - **Primary App ID:** the App ID from step 2.
   - **Domains and Subdomains:** your web domain (e.g. `getritha.com`,
     `ritha-web.onrender.com`).
   - **Return URLs:** the exact **https** URL of your login page
     (e.g. `https://ritha-web.onrender.com/login`).
4. **Verify the domain:** Apple gives you an
   `apple-developer-domain-association.txt` — host it at
   `https://<domain>/.well-known/apple-developer-domain-association.txt`, then
   click Verify.
5. Set env: `APPLE_CLIENT_ID` (backend), `VITE_APPLE_CLIENT_ID` +
   `VITE_APPLE_REDIRECT_URI` (frontend build), and redeploy.

> **No localhost for Apple.** Apple requires https + a verified domain for the
> return URL, so Apple sign-in can only be tested on staging/prod. Google works
> fine on localhost, so develop against Google and smoke-test Apple on deploy.

---

## Content-Security-Policy ⚙

If you serve a strict CSP, allow the provider SDKs:

- **Google:** `script-src https://accounts.google.com`, `frame-src https://accounts.google.com`, `connect-src https://accounts.google.com`
- **Apple:** `script-src https://appleid.cdn-apple.com`, `frame-src https://appleid.apple.com`, `connect-src https://appleid.apple.com`

Without a CSP (the default), no action needed.

---

## Testing

1. **Google (local or deployed):** open the login page → "Continue with Google" →
   pick an account → you land signed-in.
2. **Account linking:** sign in with Google using an email that already has a
   password account → you get the **same** account (check the admin: one user,
   `auth_provider` unchanged, `google_sub` now set).
3. **Apple (deployed only):** "Continue with Apple" → complete the popup → signed
   in. First sign-in captures your name; try "Hide My Email" and sign in again to
   confirm you're recognized as the same user.

Backend behavior is covered by `backend/tests/test_social_login.py` (14 tests —
new user, linking, case-insensitivity, Apple sub-matching, and every error path).

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Button doesn't appear | `VITE_*` var not set at **build** time — set it and rebuild the frontend. |
| `503 google_not_configured` / `apple_not_configured` | Backend `GOOGLE_CLIENT_ID` / `APPLE_CLIENT_ID` is empty. |
| `401 invalid_token` | Token `aud` doesn't match the configured client ID, or it's expired. For Google, the web origin isn't an authorized JS origin. For Apple, the Services ID / return URL doesn't match. |
| Google popup: `origin_mismatch` | Add the exact origin to Authorized JavaScript origins (scheme + host + port). |
| Apple popup closes with nothing | Domain not verified, or the return URL doesn't exactly match the registered one (https, no trailing-slash mismatch). |
| `400 email_unverified` (Google) | The Google account's email isn't verified — rare; user must verify with Google. |
| `400 no_email` (Apple, new user) | Apple didn't share an email and there's no existing account to match — user should sign up with email first. |

---

## Native mobile (Flutter)

The Flutter app has "Continue with Google/Apple" buttons on the login screen
(`google_sign_in` + `sign_in_with_apple` plugins). They call the **same**
backend endpoints; the buttons render only when the dart-defines below are set.

> ⚠️ Untested in CI — there's no Flutter engine in the dev sandbox, so build the
> APK and drive both flows on a device.

### Backend — audiences 🤖⚙

`GOOGLE_CLIENT_ID` is a **comma-separated allowlist** of accepted token
audiences. Native Google Sign-In is configured with the **web** client id as its
`serverClientId`, so the returned ID token's `aud` is the web client id — already
in the allowlist, **no backend change needed**. For Apple, add the app's bundle
id to the comma-separated `APPLE_CLIENT_ID` (a native iOS token's `aud` is the
bundle id, not the Services ID).

### dart-defines (passed at build) ⚙

| Define | Value |
|---|---|
| `GOOGLE_SERVER_CLIENT_ID` | your **web** Google client id (same as `VITE_GOOGLE_CLIENT_ID`) |
| `APPLE_SERVICES_ID` | your Apple Services ID (Android uses Apple's web flow) |
| `APPLE_REDIRECT_URI` | the Apple return URL that bounces back to the app |

```
flutter build apk \
  --dart-define=API_BASE_URL=https://ritha-api.onrender.com/api \
  --dart-define=GOOGLE_SERVER_CLIENT_ID=<web-client-id> \
  --dart-define=APPLE_SERVICES_ID=com.getritha.web \
  --dart-define=APPLE_REDIRECT_URI=https://ritha-api.onrender.com/auth/apple/callback
```

### Android console setup ⚙

- **Google:** in GCP, create an **Android** OAuth client for the app's package
  name + signing **SHA-1** fingerprint (`keytool -list -v -keystore …`). This
  registers the app; the `serverClientId` stays the web client id.
- **Apple:** Android has no native Apple flow — `sign_in_with_apple` opens
  Apple's web page and needs a redirect that returns to the app via an intent.
  Follow the plugin's Android setup
  (<https://pub.dev/packages/sign_in_with_apple#android>) to add the callback.

### iOS console setup ⚙ (if/when you ship iOS)

- **Google:** add the reversed-client-id URL scheme to `Info.plist`.
- **Apple:** enable the *Sign in with Apple* capability; native tokens carry the
  bundle id as `aud`, so add it to `APPLE_CLIENT_ID`.
