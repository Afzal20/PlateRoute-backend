from django.apps import AppConfig


class DeliveryConfig(AppConfig):
    name = "delivery"

    def ready(self):
        from . import handlers  # noqa: F401  register outbox handlers
