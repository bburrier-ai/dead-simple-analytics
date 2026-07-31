"""Unit tests for domain models and DB engine lifecycle."""

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from core.models import CollectPayload, EventRecord, EventType, Site, User


def test_event_record_to_db_params():
    site_id = uuid4()
    event_id = uuid4()
    record = EventRecord(
        site_id=site_id,
        event_id=event_id,
        type=EventType.click,
        path="/x",
        ip_hash="abc",
    )
    params = record.to_db_params()
    assert params["type"] == "click"
    assert params["event_id"] == str(event_id)
    assert params["site_id"] == site_id


def test_collect_payload_and_site_user_models():
    payload = CollectPayload(
        event_id=uuid4(),
        site_key="sk_x",
        type=EventType.pageview,
    )
    assert payload.type is EventType.pageview

    user = User(id=uuid4(), username="admin", password_hash="secret")
    dumped = user.model_dump()
    assert "password_hash" not in dumped
    assert dumped["username"] == "admin"

    site = Site.model_validate(
        {
            "id": uuid4(),
            "name": "Demo",
            "site_key": "sk_demo",
            "allowed_domains": ["example.com"],
            "extra_ignored": True,
        }
    )
    assert site.allowed_domains == ["example.com"]


def test_create_db_engine_and_check_connection(monkeypatch):
    from sqlalchemy.pool import NullPool

    from db import connection

    monkeypatch.setattr(connection.settings, "app_env", "production")
    engine = connection.create_db_engine("sqlite+pysqlite:///:memory:")
    assert not isinstance(engine.pool, NullPool)
    assert connection.check_db_connection(engine) is True
    engine.dispose()


def test_get_connection_commits_with_begin(monkeypatch):
    from db.connection import get_connection

    engine = MagicMock()
    conn = MagicMock()
    ctx = MagicMock()
    ctx.__enter__.return_value = conn
    ctx.__exit__.return_value = False
    engine.begin.return_value = ctx
    with get_connection(engine) as opened:
        assert opened is conn
    engine.begin.assert_called_once()


def test_readyz_requires_app_engine():
    from app.api.routers.health import readyz
    from core.exceptions import AppError

    request = MagicMock()
    request.app.state.db_engine = None
    with pytest.raises(AppError) as exc_info:
        readyz(request)
    assert exc_info.value.status_code == 503


def test_services_require_engine():
    from services.auth import AuthService
    from services.collect import CollectService
    from services.events import EventsService
    from services.sites import SitesService
    from services.stats import StatsService

    with pytest.raises(RuntimeError, match="requires a database engine"):
        AuthService().authenticate("a", "b")
    with pytest.raises(RuntimeError, match="requires a database engine"):
        CollectService()._require_engine()
    with pytest.raises(RuntimeError, match="requires a database engine"):
        EventsService()._require_engine()
    with pytest.raises(RuntimeError, match="requires a database engine"):
        SitesService()._require_engine()
    with pytest.raises(RuntimeError, match="requires a database engine"):
        StatsService()._require_engine()


def test_seed_admin_skips_when_users_exist(monkeypatch):
    from db.migrations import _seed_admin

    class FakeRepo:
        def count(self, _conn):
            return 1

        def insert(self, *_args, **_kwargs):
            raise AssertionError("should not insert")

    class ConnCtx:
        def __enter__(self):
            conn = MagicMock()
            conn.execute.return_value = None
            return conn

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("db.migrations.UsersRepository", lambda: FakeRepo())
    monkeypatch.setattr(
        "db.migrations.get_connection", lambda _engine: ConnCtx()
    )
    _seed_admin(MagicMock())
