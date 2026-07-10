import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.main import create_app
from config.settings import settings
from db import connection
from db.connection import get_connection
from db.migrations import run_migrations


@pytest.fixture(scope="session")
def test_db_url() -> str:
    return settings.test_database_url


@pytest.fixture(scope="session", autouse=True)
def setup_db(test_db_url: str, tmp_path_factory):
    settings.database_url = test_db_url
    settings.app_env = "test"
    connection._engine = None

    components = tmp_path_factory.mktemp("components")
    (components / "ok.txt").write_text("ok", encoding="utf-8")
    import app.main as main

    main.COMPONENTS_DIR = components

    run_migrations()
    yield


@pytest.fixture(scope="session")
def app_client():
    app = create_app()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client(app_client):
    app_client.cookies.clear()
    yield app_client


@pytest.fixture(autouse=True)
def clean_event_data():
    from app.api.routers import auth as auth_router
    from services import collect as collect_service

    auth_router._login_limiter.reset()
    collect_service._collect_ip_limiter.reset()
    collect_service._collect_site_limiter.reset()

    with get_connection() as conn:
        conn.execute(text("TRUNCATE events RESTART IDENTITY CASCADE"))
        conn.execute(text("TRUNCATE sites RESTART IDENTITY CASCADE"))
    yield
