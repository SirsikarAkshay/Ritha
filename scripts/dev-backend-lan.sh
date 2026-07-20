#!/usr/bin/env bash
#
# Run the Django backend for on-device (LAN) mobile testing:
#   migrate -> seed a pre-verified demo account -> serve on 0.0.0.0:8000
#
# Your Android phone (on the same WiFi) then reaches it at
#   http://<this-mac-lan-ip>:8000
# which the script prints below.
#
# Usage:  ./scripts/dev-backend-lan.sh
#
set -uo pipefail
cd "$(dirname "$0")/../backend"

PY="../.venv/bin/python"
[ -x "$PY" ] || PY="python3"   # fall back to system python if the repo venv is absent

# Prefer the interface that carries the default route (usually WiFi); fall back
# to the first private 192.168.x / 10.x address (excluding the emulator + common
# VM subnets).
IFACE="$(route -n get default 2>/dev/null | awk '/interface:/{print $2}')"
LAN_IP="$(ipconfig getifaddr "$IFACE" 2>/dev/null || true)"
if [ -z "${LAN_IP:-}" ]; then
  LAN_IP="$(ifconfig 2>/dev/null | awk '/inet /{print $2}' \
    | grep -E '^192\.168\.|^10\.' | grep -vE '^10\.0\.2\.2$|^192\.168\.64\.' | head -1)"
fi

echo "==> Migrating database (sqlite)…"
"$PY" manage.py migrate

echo "==> Seeding demo account (safe to re-run)…"
"$PY" manage.py seed_demo_user \
  || echo "   (demo seed skipped — you can still register a new account in the app)"

cat <<EOF

──────────────────────────────────────────────────────────────
  Ritha backend — LAN dev server
  Demo login:   demo@getritha.com  /  RithaDemo2026!

  Build/run the app against this Mac:
    --dart-define=API_BASE_URL=http://${LAN_IP:-<your-lan-ip>}:8000/api
    --dart-define=WS_HOST=${LAN_IP:-<your-lan-ip>}:8000

  (phone must be on the SAME WiFi as this Mac; keep this window open)
──────────────────────────────────────────────────────────────

EOF

exec env ALLOWED_HOSTS="*" DEBUG="True" "$PY" manage.py runserver 0.0.0.0:8000
