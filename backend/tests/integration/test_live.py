"""Live SSE endpoint + collect publish wiring."""

from core.live import live_hub
from tests.integration.helpers import collect, create_site, login


def test_live_requires_auth(client):
    res = client.get("/api/events/live")
    assert res.status_code == 401


def test_collect_publishes_site_id(client, monkeypatch):
    published: list[dict] = []
    monkeypatch.setattr(live_hub, "publish", published.append)

    login(client)
    site = create_site(client, name="live-site").json()
    site_id = site["id"]
    site_key = site["site_key"]

    res = collect(client, site_key, "pageview")
    assert res.status_code == 200
    assert published == [{"site_id": site_id}]


def test_duplicate_collect_does_not_publish(client, monkeypatch):
    published: list[dict] = []
    monkeypatch.setattr(live_hub, "publish", published.append)

    login(client)
    site_key = create_site(client).json()["site_key"]
    event_id = "11111111-1111-1111-1111-111111111111"

    assert collect(client, site_key, "pageview", event_id=event_id).status_code == 200
    assert len(published) == 1

    assert collect(client, site_key, "pageview", event_id=event_id).status_code == 200
    assert len(published) == 1
