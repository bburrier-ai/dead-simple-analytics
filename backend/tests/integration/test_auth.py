from config.settings import settings
from tests.integration.helpers import csrf_headers, ensure_csrf


def test_login_and_session(client):
    ensure_csrf(client)
    res = client.post(
        "/api/auth/login",
        json={"username": settings.admin_username, "password": settings.admin_password},
        headers=csrf_headers(client),
    )
    assert res.status_code == 200
    assert res.json()["user"]["username"] == settings.admin_username

    res = client.get("/api/auth/session")
    assert res.status_code == 200
    assert res.json()["user"]["username"] == settings.admin_username
