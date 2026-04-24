from django.apps import AppConfig


class RithaConfig(AppConfig):
    name           = 'ritha'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        import ritha.signals  # noqa: F401 — registers all signal handlers
