import uuid

from django.db import models


class UUIDModel(models.Model):
    """Non-guessable public identifier alongside the integer PK (§7.1)."""

    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(UUIDModel):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class RuntimeConfig(models.Model):
    """FR-ADM-03: runtime-tunable settings, cached 30 seconds."""

    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict, blank=True)
    description = models.TextField(blank=True)
    version = models.PositiveBigIntegerField(default=1)

    @classmethod
    def get(cls, key, default=None):
        from django.core.cache import cache

        cached = cache.get(f"cfg:{key}")
        if cached is None:
            row = cls.objects.filter(key=key).first()
            cached = row.value if row else default
            cache.set(f"cfg:{key}", cached, 30)
        return cached


class OutboxMessage(TimeStampedModel):
    """Transactional outbox (§4 rule 3): domain events delivered by the pump."""

    kind = models.CharField(max_length=64, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def emit(cls, kind, **payload):
        return cls.objects.create(kind=kind, payload=payload)
