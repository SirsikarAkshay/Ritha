#!/usr/bin/env bash
#
# Post-deploy smoke test for the Ritha API.
#
# Exercises the critical happy path against a *running* deployment: health,
# auth, wardrobe, region starter packs, and an AI recommendation. Uses the
# pre-verified demo account (seed it with SEED_DEMO_USER=1 or `manage.py
# seed_demo_user`) so it doesn't need the email-verification step.
#
# Usage:
#   BASE_URL=https://ritha-api.onrender.com \
#   DEMO_EMAIL=demo@getritha.com DEMO_PASSWORD='...' \
#   ./scripts/smoke_test.sh
#
# Exits non-zero if any check fails (CI-friendly).

set -uo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL="${DEMO_EMAIL:-demo@getritha.com}"
PASSWORD="${DEMO_PASSWORD:-RithaDemo2026!}"
API="${BASE_URL%/}/api"

pass=0; fail=0
green="\033[32m"; red="\033[31m"; dim="\033[2m"; rst="\033[0m"

# check <name> <expected_http> <curl-args...>
check() {
  local name="$1" want="$2"; shift 2
  local body code
  body="$(curl -sS -m 30 -w $'\n%{http_code}' "$@" 2>/dev/null)"
  code="${body##*$'\n'}"; body="${body%$'\n'*}"
  if [ "$code" = "$want" ]; then
    printf "  ${green}✓${rst} %-34s ${dim}%s${rst}\n" "$name" "$code"
    pass=$((pass+1)); LAST_BODY="$body"; return 0
  else
    printf "  ${red}✗${rst} %-34s ${red}got %s, want %s${rst}\n" "$name" "${code:-none}" "$want"
    printf "     ${dim}%s${rst}\n" "$(printf '%s' "$body" | head -c 180)"
    fail=$((fail+1)); LAST_BODY="$body"; return 1
  fi
}

json() { printf '%s' "$1" | python3 -c "import sys,json;d=json.load(sys.stdin);print(d$2)" 2>/dev/null; }

echo "▸ Ritha smoke test → $BASE_URL"
echo

# 1. Health (no auth) — Docker/Render healthcheck relies on this
check "health" 200 "$API/health/"

# 2. Auth — log in as the seeded demo user
check "login" 200 -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" "$API/auth/login/"
TOKEN="$(json "$LAST_BODY" "['access']")"
if [ -z "$TOKEN" ]; then
  echo -e "  ${red}✗ no access token — is the demo account seeded & verified?${rst}"
  fail=$((fail+1))
fi
AUTH=(-H "Authorization: Bearer $TOKEN")

# 3. Identity
check "auth/me" 200 "${AUTH[@]}" "$API/auth/me/"

# 4. Wardrobe list
check "wardrobe items" 200 "${AUTH[@]}" "$API/wardrobe/items/"

# 5. Region starter packs (onboarding data present?)
check "starter-pack regions" 200 "${AUTH[@]}" "$API/wardrobe/starter-pack/regions/"

# 6. AI recommendation — daily look (works with Mistral, degrades to stub without)
check "agents/daily-look" 200 "${AUTH[@]}" -H "Content-Type: application/json" \
  -d '{}' "$API/agents/daily-look/"

# 7. Per-place outfit (the newer engine path)
check "agents/place-outfit" 200 "${AUTH[@]}" -H "Content-Type: application/json" \
  -d '{"place":"Blue Mosque","destination":"Istanbul","place_type":"religious","formality":"smart"}' \
  "$API/agents/place-outfit/"

echo
echo "────────────────────────────────────────"
if [ "$fail" -eq 0 ]; then
  printf "${green}✓ all %d checks passed${rst}\n" "$pass"
  exit 0
else
  printf "${red}✗ %d passed, %d failed${rst}\n" "$pass" "$fail"
  exit 1
fi
