from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # ensure signals/adapters modules are discoverable if needed
        from . import adapters  # noqa: F401
