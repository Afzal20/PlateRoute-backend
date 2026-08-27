from django.apps import AppConfig


class AccountConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    label = "accounts"

    def ready(self):
        import accounts.signals  # noqa: F401
        import accounts.schema  # noqa: F401
