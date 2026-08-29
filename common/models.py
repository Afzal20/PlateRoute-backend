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
    def _cache_key(cls, key):
        # Bind cache to the current version so bump-on-write invalidates reads.
        version = cls.objects.values_list("version", flat=True).filter(key=key).first() or 0
        return f"cfg:{key}:v{version}"

    @classmethod
    def get(cls, key, default=None):
        from django.core.cache import cache

        try:
            cached = cache.get(cls._cache_key(key))
            if cached is None:
                row = cls.objects.filter(key=key).first()
                cached = row.value if row else default
                cache.set(cls._cache_key(key), cached, 30)
            return cached
        except Exception:
            return default


class OutboxMessage(TimeStampedModel):
    """Transactional outbox (§4 rule 3): domain events delivered by the pump."""

    kind = models.CharField(max_length=64, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    @classmethod
    def emit(cls, kind, **payload):
        return cls.objects.create(kind=kind, payload=payload)
