"""Shared helpers so per-app test files stay tiny."""
from django.contrib.auth import get_user_model


def make_user(email="a@test.io", password="Str0ngPass!x", role="customer"):
    return get_user_model().objects.create_user(email=email, password=password, role=role)


def api(client, user, method, path, data=None, **kw):
    """Authenticated DRF request helper; path is relative to /api."""
    if user:
        client.force_authenticate(user)
    return getattr(client, method)(f"/api{path}", data, format="json", **kw)
