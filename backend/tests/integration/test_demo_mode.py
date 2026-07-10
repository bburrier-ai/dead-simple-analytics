from config.settings import settings
from demo import mode as demo_mode
from tests.integration.helpers import ensure_csrf, login


def test_demo_unavailable_in_production(client):
    settings.app_env = "production"
    try:
        res = client.get("/api/demo-mode")
        assert res.status_code == 200
        assert res.json() == {"available": False, "enabled": False}
    finally:
        settings.app_env = "test"


def test_demo_enabled_returns_fixtures(client):
    settings.app_env = "local"
    client.cookies.set(demo_mode.COOKIE_NAME, demo_mode.COOKIE_ENABLED)

    login(client)

    sites = client.get("/api/sites").json()["items"]
    assert len(sites) == 2
    assert sites[0]["name"] == "demo.example.com"

    site_id = sites[0]["id"]
    events = client.get(f"/api/events?site_id={site_id}").json()
    assert events["total"] >= 5
    assert all(item.get("session_id") for item in events["items"])

    stats = client.get(f"/api/stats/visits?site_id={site_id}&days=14").json()
    assert stats["totals"]["pageviews"] > 0
    daily_peak = max(row["visitors"] for row in stats["series"])
    assert stats["totals"]["visitors"] > daily_peak

    hour_stats = client.get(f"/api/stats/visits?site_id={site_id}&hours=24").json()
    hour_peak = max(row["visitors"] for row in hour_stats["series"])
    assert hour_stats["totals"]["visitors"] > hour_peak

    html = client.get(f"/partials/events-table?site_id={site_id}").text
    assert "pageview" in html
    assert "sess_8f2a1c" in html

    settings.app_env = "test"


def test_demo_toggle_cookie(client):
    settings.app_env = "local"
    ensure_csrf(client)
    token = client.cookies.get(settings.csrf_cookie_name)
    res = client.post(
        "/demo-mode",
        data={"enabled": "0", "redirect": "/", "csrf_token": token},
        follow_redirects=False,
    )
    assert res.status_code == 303
    assert demo_mode.COOKIE_DISABLED in res.headers.get("set-cookie", "")
    settings.app_env = "test"
