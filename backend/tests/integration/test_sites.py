from tests.integration.helpers import create_site, csrf_headers, login


def _create_site(client, name="Test site", domains=None):
    return create_site(
        client,
        name=name,
        allowed_domains=domains or ["example.com"],
    )


def test_update_site(client):
    login(client)
    site = _create_site(client).json()

    res = client.patch(
        f"/api/sites/{site['id']}",
        json={
            "name": "Renamed site",
            "allowed_domains": ["example.com", "www.example.com"],
            "site_key": "sk_custom_key_123",
        },
        headers=csrf_headers(client),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "Renamed site"
    assert data["allowed_domains"] == ["example.com", "www.example.com"]
    assert data["site_key"] == "sk_custom_key_123"
    assert 'data-site="sk_custom_key_123"' in data["snippet"]


def test_update_site_rejects_duplicate_site_key(client):
    login(client)
    first = _create_site(client, name="First").json()
    second = _create_site(client, name="Second", domains=["other.com"]).json()

    res = client.patch(
        f"/api/sites/{second['id']}",
        json={
            "name": "Second",
            "allowed_domains": ["other.com"],
            "site_key": first["site_key"],
        },
        headers=csrf_headers(client),
    )
    assert res.status_code == 400


def test_create_site_requires_csrf(client):
    login(client)
    res = client.post(
        "/api/sites",
        json={"name": "no-csrf", "allowed_domains": ["example.com"]},
    )
    assert res.status_code == 403