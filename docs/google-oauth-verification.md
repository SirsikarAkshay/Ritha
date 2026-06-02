# Google OAuth Verification — Ritha

Material for the Google Cloud Console **OAuth consent screen** verification
submission. Microsoft/Outlook (Azure app verification) and Apple are separate,
lighter processes — notes at the bottom.

> Before submitting: deploy is live, the Privacy Policy (operator: Ritha GmbH) is
> published at the URL below, and the remaining `[REGISTERED ADDRESS]` placeholder
> in the policy is filled in.

## App summary
Ritha is an AI wardrobe and travel styling assistant. It recommends outfits
based on the user's wardrobe, the weather, and their calendar, and builds
packing lists and cultural guidance for trips. Connecting a calendar is optional
and user-initiated; it lets Ritha suggest appropriate outfits for upcoming events.

- **App name:** Ritha
- **User type:** External
- **Authorized domain:** `getritha.com` (and `onrender.com` until a custom domain is attached)
- **App home page:** `https://ritha-web.onrender.com`
- **Privacy policy URL:** `https://ritha-web.onrender.com/privacy`
- **Terms URL:** `https://ritha-web.onrender.com/terms`
- **Authorized redirect URI:** `https://ritha-api.onrender.com/api/calendar/google/callback/`

## Requested scopes & per-scope justification
Defined in `backend/ritha/settings.py` (`GOOGLE_CALENDAR_SCOPES`):

| Scope | Justification |
|---|---|
| `https://www.googleapis.com/auth/calendar.readonly` | Read the user's upcoming events (title, time, location) to infer the occasion and formality of each day, so Ritha can recommend a suitable outfit and flag schedule/weather conflicts. Read-only — Ritha never creates, edits, or deletes events. |
| `https://www.googleapis.com/auth/userinfo.email` | Identify which Google account is connected, so the user can see and manage the connected account and we can de-duplicate events across sources. |

Both are the **minimum** scopes needed for the calendar-aware outfit feature. We
request no broader Gmail, Drive, or contacts scopes.

## How the data is used, stored, retained, and deleted
- **Used** only to power outfit recommendations and conflict detection for the signed-in user.
- **Stored:** event fields needed for recommendations, plus an encrypted OAuth refresh token, in our database (hosted on Render, EU region). Tokens are encrypted at rest.
- **Retained** while the calendar stays connected. Disconnecting (Profile → Account) deletes the stored tokens and stops syncing. Deleting the account removes all associated data.
- **Not** sold, **not** used for advertising, **not** read by humans (except for security/abuse, with consent, or as legally required), and **not** used to train generalized AI/ML models.

## Limited Use compliance statement
> Ritha's use and transfer of information received from Google APIs to any other
> app will adhere to the [Google API Services User Data Policy](https://developers.google.com/terms/api-services-user-data-policy),
> including the Limited Use requirements.

(This statement is also reproduced in the published Privacy Policy, section 3.)

## Demo video — outline
Google requires a short video showing the OAuth grant and the data in use:
1. Show the app home page and the privacy policy URL in the address bar.
2. Sign in → Profile → "Connect Google Calendar".
3. Show the Google consent screen, with the requested scopes visible, and grant.
4. Return to the app; open the dashboard/itinerary and show that an upcoming
   calendar event now drives an outfit recommendation.
5. Show Profile → "Disconnect" to demonstrate revocation.

## Microsoft / Outlook (Azure)
Register the app in Azure AD, request delegated `Calendars.Read` + `User.Read`,
add the same privacy/terms URLs, and (for many users) submit for Microsoft
publisher verification. Redirect URI: `https://ritha-api.onrender.com/api/calendar/outlook/callback/`.

## Apple Calendar
Apple CalDAV uses an app-specific password the user provides directly — no OAuth
consent screen or Apple verification step is required.
