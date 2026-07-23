# Ritha — Go-Live Checklist

Everything between "CI is green" and "people can use it." The code and deploy
config (`render.yaml`, `backend/Dockerfile`, `backend/entrypoint.sh`) are ready —
this is the operational path to a live app.

**Legend:** ⚙ you do it · 🤖 automated · ⚠️ critical

---

## 0 · Accounts you'll need

- [ ] **Render** account — hosts Postgres + Redis + API + workers + the web build. ⚙
- [ ] **Object storage — AWS S3 or Cloudflare R2** — for uploaded wardrobe photos; Render's disk is ephemeral. ⚙ ⚠️
- [ ] **Mistral API key** — powers recommendations, cultural advice & snap-to-add; without it the AI silently falls back to rule-based stubs. ⚙
- [ ] **Resend** account + verified `getritha.com` sending domain — transactional email (already wired via Anymail). ⚙

## 1 · Set secrets in Render

Fill the `sync:false` values in **Render → Env Groups → `ritha-config`** (see `render.yaml`).

> ⚠️ **Storage is not optional.** Set `AWS_STORAGE_BUCKET_NAME` + keys, or every
> wardrobe photo (and starter-pack image) is wiped on each deploy/restart.

- [ ] `AWS_STORAGE_BUCKET_NAME` + `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` (+ `AWS_REGION` or R2 endpoint) — activates S3 media. ⚙ ⚠️
- [ ] `MISTRAL_API_KEY` — real AI vs stubbed AI. ⚙
- [ ] `RESEND_API_KEY` (confirm `DEFAULT_FROM_EMAIL` uses `getritha.com`) — email verify & reset. ⚙
- [ ] *Optional:* Google/Microsoft OAuth secrets, `SENTRY_DSN` — calendar sync + error monitoring. ⚙
- [ ] *Optional:* **Sign in with Google/Apple** — set `GOOGLE_CLIENT_ID` / `APPLE_CLIENT_ID` (backend) + the `VITE_*` client IDs (frontend build). Full console + env steps: [`docs/social-login-setup.md`](social-login-setup.md). ⚙
- [ ] `SEED_DEMO_USER=1` (+ a strong `DEMO_PASSWORD`) — auto-seeds the pre-verified demo account on deploy. ⚙

## 2 · First deploy

- [ ] **Render → New → Blueprint → point at the repo** — provisions everything from `render.yaml`. ⚙
- [ ] **Watch the API service logs** — the entrypoint runs `migrate` → `collectstatic` → `seed_cultural_data` → `setup_celery_beat` automatically; wait for `Starting: daphne`. 🤖

> 🗓️ **Free Postgres is deleted after 30 days.** Upgrade `ritha-db` to a paid plan before any real launch.

## 3 · Wire CI auto-deploy

- [ ] **Create a Deploy Hook** for each service (Render → ritha-api / -worker / -beat / -web → Settings → Deploy Hook). ⚙
- [ ] **Add them as GitHub Actions secrets:** `RENDER_DEPLOY_HOOK_API`, `_WORKER`, `_BEAT`, `_WEB`. Then every green merge to `main` deploys. ⚙ → 🤖
- [ ] *(Recommended)* Branch-protect `main` to require the CI checks. ⚙

## 4 · Verify the live app

- [ ] **Run the post-deploy smoke test** — health → login → wardrobe → regions → recommendation; exits non-zero on any failure. ⚙

  ```bash
  BASE_URL=https://ritha-api.onrender.com \
  DEMO_PASSWORD='...' ./scripts/smoke_test.sh
  ```

- [ ] **Fetch the starter-pack photos, then re-seed** — otherwise onboarding shows illustrations, not real photos. Run once (needs internet + the ML deps locally), review, commit. ⚙

  ```bash
  python manage.py fetch_starter_images --region south_asian_north
  python manage.py fetch_starter_images --region south_asian_tropical
  # review backend/wardrobe/seed_images/, then:
  python manage.py seed_starter_packs
  ```

- [ ] **Manual pass:** register → onboard → plan a trip. Confirm the email arrives (Resend), the region wardrobe appears, and a trip returns packing + places + a per-place outfit. ⚙

## 5 · Domain & launch

- [ ] **Point `getritha.com` at Render** (Cloudflare DNS) — add the custom domain to `ritha-web` (and `api.getritha.com` to `ritha-api`). Then update `VITE_API_BASE_URL`, `WEB_APP_URL`, `CSRF_TRUSTED_ORIGINS`, and the Google redirect URI. ⚙
- [ ] **Ship the reels** — record the `marketing/reels/` library to MP4 and post; run the influencer outreach. ⚙
- [ ] **Watch Sentry + Render metrics** for the first traffic. ⚙

---

## Notes verified against the code

- **Snap-to-add** uses **Mistral vision** (`POST /api/wardrobe/analyze-image/`), not the
  torch classifier — so `requirements_prod.txt` ships **no torch** and the lean image is
  fine. It just needs `MISTRAL_API_KEY`.
- Recommendations degrade gracefully with no ML artifacts and no torch (numpy-only
  scoring), so the engine works on a lean deploy out of the box.
- `ALLOWED_HOSTS` auto-appends `RENDER_EXTERNAL_HOSTNAME`; `SECRET_KEY` is required when
  `DEBUG=False`; DB connections require TLS (`sslmode=require`).

An interactive version of this checklist (with saved progress) is also available as a
shareable page — ask the team lead for the link.
