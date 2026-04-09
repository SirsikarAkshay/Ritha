from django.apps import AppConfig


class SocialConfig(AppConfig):
    name = 'social'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        from . import signals  # noqa: F401
