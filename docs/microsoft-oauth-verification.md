# Microsoft / Outlook OAuth — App Registration & Publisher Verification (Ritha)

Setup + verification material for the **Microsoft Entra ID (Azure AD)** app
registration that backs Outlook/Microsoft 365 calendar sync. This is the
Microsoft analog of `google-oauth-verification.md`. Google is a separate process;
Apple CalDAV needs none (it uses an app-specific password the user supplies).

> Microsoft is generally lighter than Google here: the scopes Ritha uses are
> standard **delegated** permissions that don't need a security review or a demo
> video. The main "verification" step is **Publisher Verification** (verifying
> your domain), which removes the "unverified app" banner and raises consent limits.

## App summary
Ritha is an AI wardrobe and travel styling assistant. Connecting Outlook is
optional and user-initiated; it lets Ritha read upcoming calendar events to
suggest appropriate outfits and flag schedule/weather conflicts.

- **App name:** Ritha
- **Publisher / app home page:** `https://ritha-web.onrender.com`
- **Privacy statement URL:** `https://ritha-web.onrender.com/privacy`
- **Terms of service URL:** `https://ritha-web.onrender.com/terms`
- **Redirect URI (Web platform):** `https://ritha-api.onrender.com/api/calendar/outlook/callback/`
- **Auth library / authority:** MSAL confidential client, authority `https://login.microsoftonline.com/common`

## App registration (Microsoft Entra admin center → App registrations)
1. **New registration.**
   - Supported account types: **Accounts in any organizational directory and personal Microsoft accounts** (this matches the `/common` authority — Work/School + personal Outlook.com).
   - Redirect URI: platform **Web**, value `https://ritha-api.onrender.com/api/calendar/outlook/callback/` (add the `http://localhost:8000/...` one too for local dev).
2. **Certificates & secrets → New client secret.** Put the value in `MICROSOFT_CLIENT_SECRET`, the Application (client) ID in `MICROSOFT_CLIENT_ID` (both already wired as `sync:false` env vars in `render.yaml`).
3. **API permissions → Microsoft Graph → Delegated permissions:** add `Calendars.Read` and `User.Read`. (`offline_access` is requested at runtime for refresh tokens and is a standard OpenID permission — no entry needed.) Grant/admin-consent is **not** required for these delegated scopes in most tenants; users consent individually.
4. **Branding & properties:** set the app name, logo, publisher domain, and the privacy/terms URLs above.

## Requested scopes & per-scope justification
From `backend/calendar_sync/outlook_calendar.py` (`SCOPES`):

| Scope | Type | Justification |
|---|---|---|
| `Calendars.Read` | Delegated | Read the user's upcoming events (subject, time, location) to infer occasion/formality and recommend a suitable outfit. Read-only — Ritha never creates, edits, or deletes events. |
| `User.Read` | Delegated | Read the signed-in user's basic profile/email to identify the connected Microsoft account and de-duplicate events across sources. |
| `offline_access` | Delegated (OIDC) | Obtain a refresh token so syncing continues without re-prompting; standard, not a Graph resource permission. |

These are the **minimum** delegated scopes for the calendar-aware outfit feature.
No application (app-only) permissions, no mail, files, or directory scopes.

## How the data is used, stored, retained, deleted
- **Used** only to power outfit recommendations and conflict detection for the signed-in user.
- **Stored:** the event fields needed for recommendations, plus an encrypted OAuth refresh token, in our database (hosted on Render, EU region; tokens encrypted at rest).
- **Retained** while Outlook stays connected. Disconnecting (Profile → Account) deletes the stored token and stops syncing; deleting the account removes all associated data.
- **Not** sold, **not** used for advertising, **not** read by humans (except for security/abuse, with consent, or as legally required), and **not** used to train generalized AI/ML models. (Mirrors the Privacy Policy, section 3.)

## Publisher Verification (the actual "verification" step)
This is what removes the "unverified" consent warning and raises the consent cap.
1. Have (or join) a **Microsoft Partner Network / Cloud Partner Program** account with a verified **Partner ID (MPN ID)**.
2. In Entra → **App registrations → [Ritha] → Branding & properties → Publisher domain**, set and verify a domain you control (e.g. `getritha.com`) via the published `.well-known/microsoft-identity-association.json` or DNS TXT method.
3. **Verify publisher:** associate the verified MPN ID with the app registration → "Mark as publisher verified." A green "verified" badge then shows on the consent screen.

## Admin consent (enterprise users)
`Calendars.Read`/`User.Read` are user-consentable by default. Some organizations
disable user consent; in that case a tenant admin must approve once via the
admin-consent flow (the admin opens the consent URL and grants for the org).
No action needed on our side beyond pointing such users to their IT admin.

## Notes
- **Google** Calendar verification is a separate, heavier process (sensitive-scope review + demo video) — see `google-oauth-verification.md`.
- **Apple** Calendar uses CalDAV with a user-provided app-specific password — no OAuth consent screen or Apple verification required.
