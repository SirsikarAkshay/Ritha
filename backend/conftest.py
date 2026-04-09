import pytest


def pytest_configure(config):
    """Runs before any collection — patch ALLOWED_HOSTS early."""
    from django.conf import settings
    settings.ALLOWED_HOSTS = ['*', 'testserver']


@pytest.fixture(autouse=True)
def disable_throttling_and_cache(settings):
    """
    Applied to every test automatically.
    - Strips all throttle classes so login calls never 429
    - Uses DummyCache so throttle counters don't bleed between tests
    """
    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        'DEFAULT_THROTTLE_CLASSES': [],
        'DEFAULT_THROTTLE_RATES': {
            'anon':               '99999/day',
            'user':               '99999/day',
            'ai_agents':          '99999/day',
            'resend_verification': '99999/day',
            'login_attempts':      '99999/day',
            'password_reset':      '99999/day',
        },
    }
    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }
