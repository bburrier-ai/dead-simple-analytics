from config.settings import settings
from tests.integration.helpers import csrf_headers, ensure_csrf, login


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


def test_unauthenticated_pages_redirect_to_login(client):
    for path in ("/", "/sites"):
        res = client.get(path, follow_redirects=False)
        assert res.status_code == 302, path
        assert res.headers["location"] == "/login", path

    res = client.get("/dashboard", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"] == "/"


def test_authenticated_pages_serve_html(client):
    login(client)
    for path, needle in (("/", "Dashboard"), ("/sites", "Sites")):
        res = client.get(path, follow_redirects=False)
        assert res.status_code == 200, path
        assert needle in res.text


def test_login_page_redirects_when_authenticated(client):
    login(client)
    res = client.get("/login", follow_redirects=False)
    assert res.status_code == 302
    assert res.headers["location"] == "/"
