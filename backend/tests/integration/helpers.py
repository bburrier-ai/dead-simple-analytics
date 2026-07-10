"""Shared helpers for integration tests."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi.testclient import TestClient

from config.settings import settings


def ensure_csrf(client: TestClient) -> str:
    client.get("/api/auth/csrf")
    token = client.cookies.get(settings.csrf_cookie_name)
    assert token
    return token


def csrf_headers(client: TestClient) -> dict[str, str]:
    token = client.cookies.get(settings.csrf_cookie_name) or ensure_csrf(client)
    return {"X-CSRF-Token": token}


def login(client: TestClient) -> None:
    ensure_csrf(client)
    res = client.post(
        "/api/auth/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
        headers=csrf_headers(client),
    )
    assert res.status_code == 200, res.text


def create_site(client: TestClient, **overrides: Any):
    return client.post(
        "/api/sites",
        json={"name": "test-site", "allowed_domains": ["localhost"], **overrides},
        headers=csrf_headers(client),
    )


def collect(
    client: TestClient,
    site_key: str,
    event_type: str,
    *,
    event_id: str | None = None,
    **extra: Any,
):
    payload = {
        "event_id": event_id or str(uuid.uuid4()),
        "site_key": site_key,
        "type": event_type,
        "path": "/test",
        "title": "Test",
        "visitor_id": "test-visitor-001",
        "visitor_hash": "a" * 64,
        "session_id": "test-sess-001",
        **extra,
    }
    return client.post(
        "/collect",
        json=payload,
        headers={"Origin": "http://localhost:8082"},
    )
