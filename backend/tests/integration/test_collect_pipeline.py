"""End-to-end: collect → API → dashboard partials."""

from tests.integration.helpers import collect, create_site, login


def test_ingestion_propagates_to_api_and_ui(client):
    login(client)

    site_res = create_site(client, name="e2e-site")
    assert site_res.status_code == 200
    site = site_res.json()
    site_id = site["id"]
    site_key = site["site_key"]

    for event_type, track_id in [
        ("pageview", None),
        ("hover", "cta-test"),
        ("click", "cta-test"),
    ]:
        res = collect(client, site_key, event_type, track_id=track_id)
        assert res.status_code == 200, res.text
        assert res.json() == {"ok": True}

    events_res = client.get(f"/api/events?site_id={site_id}&limit=10")
    assert events_res.status_code == 200
    data = events_res.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    types = {item["type"] for item in data["items"]}
    assert types == {"pageview", "hover", "click"}

    for item in data["items"]:
        assert item["session_id"] == "test-sess-001"
        assert item["visitor_id"] == "test-visitor-001"

    stats_res = client.get(f"/api/stats/visits?site_id={site_id}&days=7")
    assert stats_res.status_code == 200
    totals = stats_res.json()["totals"]
    assert totals["pageviews"] >= 1
    assert totals["clicks"] >= 1
    assert totals["hovers"] >= 1
    assert totals["visitors"] == 1

    partial_res = client.get(f"/partials/events-table?site_id={site_id}")
    assert partial_res.status_code == 200
    html = partial_res.text
    assert "pageview" in html
    assert "hover" in html
    assert "click" in html
    assert "cta-test" in html
    assert "test-sess" in html


def test_same_visitor_hash_counts_once_across_visitor_ids(client):
    login(client)
    site_key = create_site(client, name="e2e-site").json()["site_key"]
    site_id = client.get("/api/sites").json()["items"][0]["id"]

    for visitor_id in ("visitor-a", "visitor-b"):
        res = collect(
            client,
            site_key,
            "pageview",
            visitor_id=visitor_id,
            visitor_hash="a" * 64,
        )
        assert res.status_code == 200

    stats = client.get(f"/api/stats/visits?site_id={site_id}&days=7").json()
    assert stats["totals"]["visitors"] == 1


def test_collect_rejects_disallowed_origin(client):
    import uuid

    login(client)
    site_key = create_site(client).json()["site_key"]
    res = client.post(
        "/collect",
        json={
            "event_id": str(uuid.uuid4()),
            "site_key": site_key,
            "type": "pageview",
            "path": "/",
            "session_id": "test-sess-001",
        },
        headers={"Origin": "https://evil.example"},
    )
    assert res.status_code == 403
