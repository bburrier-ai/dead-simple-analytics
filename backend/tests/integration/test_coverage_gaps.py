"""Integration coverage for remaining HTTP / service paths."""

from __future__ import annotations

import uuid

from config.settings import settings
from demo import mode as demo_mode
from services.auth import AuthService
from tests.integration.helpers import collect, create_site, csrf_headers, ensure_csrf, login


def test_logout_and_me(client):
    login(client)
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["username"] == settings.admin_username

    res = client.post("/api/auth/logout", headers=csrf_headers(client))
    assert res.status_code == 200
    assert res.json()["ok"] is True
    assert client.get("/api/auth/me").status_code == 401


def test_session_invalid_and_missing_user(client):
    assert client.get("/api/auth/session").json()["user"] is None

    client.cookies.set(settings.session_cookie_name, "invalid.token.value")
    assert client.get("/api/auth/session").json()["user"] is None

    token = AuthService().create_token(uuid.uuid4())
    client.cookies.set(settings.session_cookie_name, token)
    assert client.get("/api/auth/session").json()["user"] is None


def test_collect_options_and_cors(client):
    res = client.options("/collect")
    assert res.status_code == 204

    login(client)
    site_key = create_site(client, allowed_domains=["localhost"]).json()["site_key"]
    posted = collect(client, site_key, "pageview")
    assert posted.status_code == 200
    assert posted.headers.get("access-control-allow-origin") == "*"


def test_favicon_and_login_html(client):
    assert client.get("/favicon.ico").status_code == 200
    res = client.get("/login", follow_redirects=False)
    assert res.status_code == 200
    assert "login" in res.text.lower() or "password" in res.text.lower()


def test_login_redirect_when_authenticated(client):
    login(client)
    res = client.get("/login", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"] == "/"
    assert client.get("/", follow_redirects=False).status_code == 200


def test_empty_sites_partial(client):
    login(client)
    html = client.get("/partials/sites-table").text
    assert "No sites yet" in html


def test_me_unknown_user_token(client):
    token = AuthService().create_token(uuid.uuid4())
    client.cookies.set(settings.session_cookie_name, token)
    assert client.get("/api/auth/me").status_code == 401


def test_partials_sites_and_empty_events(client):
    login(client)
    create_site(client)
    sites_html = client.get("/partials/sites-table").text
    assert "Test w/curl" in sites_html
    assert "data-curl-test=" in sites_html

    site_id = client.get("/api/sites").json()["items"][0]["id"]
    empty = client.get(f"/partials/events-table?site_id={site_id}").text
    assert "No events match" in empty


def test_events_filter_query_and_type(client):
    login(client)
    site = create_site(client, allowed_domains=["localhost"]).json()
    assert collect(client, site["site_key"], "pageview").status_code == 200
    assert (
        collect(
            client,
            site["site_key"],
            "click",
            track_id="cta-signup",
            path="/pricing",
        ).status_code
        == 200
    )

    filtered = client.get(
        f"/api/events?site_id={site['id']}&type=click&q=pricing&sort=path&order=asc"
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] >= 1

    html = client.get(
        f"/partials/events-table?site_id={site['id']}&type=click&q=cta&sort=path&order=asc"
    ).text
    assert "click" in html


def test_get_site_and_stats_hours(client):
    login(client)
    site = create_site(client).json()
    got = client.get(f"/api/sites/{site['id']}")
    assert got.status_code == 200
    assert got.json()["site_key"] == site["site_key"]
    assert client.get(f"/api/sites/{uuid.uuid4()}").status_code == 404

    stats = client.get(f"/api/stats/visits?site_id={site['id']}&hours=24")
    assert stats.status_code == 200
    assert "totals" in stats.json()


def test_demo_mode_blocks_site_writes_and_serves_demo_get(client):
    settings.app_env = "local"
    try:
        login(client)
        client.cookies.set(demo_mode.COOKIE_NAME, demo_mode.COOKIE_ENABLED)

        res = client.post(
            "/api/sites",
            json={"name": "x", "allowed_domains": ["example.com"]},
            headers=csrf_headers(client),
        )
        assert res.status_code == 403

        sites = client.get("/api/sites").json()["items"]
        assert sites
        demo_id = sites[0]["id"]
        assert client.get(f"/api/sites/{demo_id}").status_code == 200
        assert client.get(f"/api/sites/{uuid.uuid4()}").status_code == 404

        patch = client.patch(
            f"/api/sites/{demo_id}",
            json={
                "name": "n",
                "allowed_domains": ["example.com"],
                "site_key": "sk_x",
            },
            headers=csrf_headers(client),
        )
        assert patch.status_code == 403

        assert "Test w/curl" in client.get("/partials/sites-table").text
        assert client.get(f"/api/stats/visits?site_id={demo_id}&days=7").status_code == 200
        assert client.get(f"/api/stats/visits?site_id={demo_id}&hours=24").status_code == 200
    finally:
        settings.app_env = "test"


def test_demo_mode_unavailable_post(client):
    settings.app_env = "production"
    try:
        ensure_csrf(client)
        token = client.cookies.get(settings.csrf_cookie_name)
        res = client.post(
            "/demo-mode",
            data={"enabled": "1", "redirect": "https://evil.example", "csrf_token": token},
            follow_redirects=False,
        )
        assert res.status_code == 403
    finally:
        settings.app_env = "test"


def test_static_component_routes(client, monkeypatch):
    monkeypatch.setattr(settings, "components_cdn_url", "  ")
    assert client.get("/components/ok.txt").status_code == 200
    cfg = client.get("/components-config.js")
    assert cfg.status_code == 200
    assert "/components" in cfg.text
    assert client.get("/dsa.js").status_code == 200


def test_collect_error_paths(client):
    login(client)
    site_key = create_site(client, allowed_domains=["localhost"]).json()["site_key"]

    assert collect(client, "sk_missing", "pageview").status_code == 404

    bad_type = client.post(
        "/collect",
        json={
            "event_id": str(uuid.uuid4()),
            "site_key": site_key,
            "type": "nope",
            "path": "/",
        },
        headers={"Origin": "http://localhost"},
    )
    assert bad_type.status_code == 403

    no_origin = client.post(
        "/collect",
        json={
            "event_id": str(uuid.uuid4()),
            "site_key": site_key,
            "type": "pageview",
            "path": "/",
        },
    )
    assert no_origin.status_code == 403

    bad_origin = client.post(
        "/collect",
        json={
            "event_id": str(uuid.uuid4()),
            "site_key": site_key,
            "type": "pageview",
            "path": "/",
        },
        headers={"Origin": "https://evil.example"},
    )
    assert bad_origin.status_code == 403


def test_site_rate_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "collect_rate_limit_per_min", 1000)
    monkeypatch.setattr(settings, "collect_site_rate_limit_per_min", 1)
    login(client)
    site_key = create_site(client, allowed_domains=["localhost"]).json()["site_key"]
    assert collect(client, site_key, "pageview").status_code == 200
    assert collect(client, site_key, "pageview").status_code == 429


def test_update_missing_site(client):
    login(client)
    res = client.patch(
        f"/api/sites/{uuid.uuid4()}",
        json={
            "name": "gone",
            "allowed_domains": ["example.com"],
            "site_key": "sk_gone_key",
        },
        headers=csrf_headers(client),
    )
    assert res.status_code == 404
