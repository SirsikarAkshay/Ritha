from django.apps import AppConfig


class ArokahConfig(AppConfig):
    name           = 'arokah'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        import arokah.signals  # noqa: F401 — registers all signal handlers
