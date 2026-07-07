#!/bin/sh
set -e

# Release tasks (migrate / collectstatic / seed) run once per deploy. Only the
# web service should run them; the worker and beat set RUN_RELEASE_TASKS=0 so
# they don't race each other migrating the same database on startup.
if [ "${RUN_RELEASE_TASKS:-1}" = "1" ]; then
    echo "==> Running database migrations..."
    python manage.py migrate --noinput

    echo "==> Collecting static files..."
    python manage.py collectstatic --noinput --clear 2>/dev/null || true

    echo "==> Seeding cultural data (idempotent)..."
    python manage.py seed_cultural_data 2>/dev/null || true

    echo "==> Setting up Celery Beat schedules..."
    python manage.py setup_celery_beat 2>/dev/null || true

    # Optional: seed a fully-populated, pre-verified demo account for showing the
    # app to influencers/investors without email setup. Off by default; enable by
    # setting SEED_DEMO_USER=1 (and optionally DEMO_EMAIL / DEMO_PASSWORD).
    if [ "${SEED_DEMO_USER:-0}" = "1" ]; then
        echo "==> Seeding demo account..."
        python manage.py seed_demo_user || true
    fi
else
    echo "==> RUN_RELEASE_TASKS=0 — skipping migrate/collectstatic/seed."
fi

echo "==> Starting: $@"
exec "$@"
