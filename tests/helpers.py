"""Shared helpers so per-app test files stay tiny."""
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient


def make_user(email="a@test.io", password="Str0ngPass!x", role="customer"):
    return get_user_model().objects.create_user(email=email, password=password, role=role)


def api(user, method, path, data=None, **kw):
    """Authenticated DRF request helper; path is relative to /api."""
    client = APIClient()
    client.force_authenticate(user) if user else None
    kwargs = {"format": "json", **kw} if data is not None else kw
    return getattr(client, method)(f"/api{path}", data, **kwargs)

