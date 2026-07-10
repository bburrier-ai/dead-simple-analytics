import uuid

from config.settings import settings
from tests.integration.helpers import collect, create_site, csrf_headers, ensure_csrf, login


def test_collect_rejects_replayed_event_id(client):
    login(client)
    site_key = create_site(client, allowed_domains=["localhost"]).json()["site_key"]
    event_id = str(uuid.uuid4())

    first = collect(client, site_key, "pageview", event_id=event_id)
    replay = collect(client, site_key, "pageview", event_id=event_id)

    assert first.status_code == 200
    assert replay.status_code == 200

    site_id = client.get("/api/sites").json()["items"][0]["id"]
    events = client.get(f"/api/events?site_id={site_id}&limit=10").json()
    assert events["total"] == 1


def test_login_rate_limited(client, monkeypatch):
    monkeypatch.setattr(settings, "login_rate_limit_attempts", 2)
    monkeypatch.setattr(settings, "login_rate_limit_window_sec", 900)

    ensure_csrf(client)
    for _ in range(2):
        res = client.post(
            "/api/auth/login",
            json={"username": settings.admin_username, "password": "wrong-password"},
            headers=csrf_headers(client),
        )
        assert res.status_code == 401

    blocked = client.post(
        "/api/auth/login",
        json={"username": settings.admin_username, "password": "wrong-password"},
        headers=csrf_headers(client),
    )
    assert blocked.status_code == 429


def test_collect_rate_limited_per_ip(client, monkeypatch):
    monkeypatch.setattr(settings, "collect_rate_limit_per_min", 2)
    monkeypatch.setattr(settings, "collect_site_rate_limit_per_min", 1000)

    login(client)
    site_key = create_site(client, allowed_domains=["localhost"]).json()["site_key"]

    assert collect(client, site_key, "pageview").status_code == 200
    assert collect(client, site_key, "pageview").status_code == 200
    assert collect(client, site_key, "pageview").status_code == 429


def test_login_requires_csrf(client):
    ensure_csrf(client)
    res = client.post(
        "/api/auth/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
        headers={"X-CSRF-Token": "invalid-token"},
    )
    assert res.status_code == 403
