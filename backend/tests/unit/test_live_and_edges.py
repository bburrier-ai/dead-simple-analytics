"""Unit tests for remaining service / migration edges."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.schemas import CollectEvent
from core.exceptions import ForbiddenError
from core.models import EventType
from db.migrations import _seed_admin
from services.auth import AuthService
from services.collect import CollectService


def _engine_with_conn(conn: MagicMock | None = None) -> tuple[MagicMock, MagicMock]:
    conn = conn or MagicMock()
    engine = MagicMock()
    ctx = MagicMock()
    ctx.__enter__.return_value = conn
    ctx.__exit__.return_value = False
    engine.begin.return_value = ctx
    return engine, conn


def test_collect_missing_site_key_and_empty_domains():
    engine, _conn = _engine_with_conn()
    svc = CollectService(engine)
    with pytest.raises(ForbiddenError, match="Missing site_key"):
        svc.ingest(
            CollectEvent(
                event_id="11111111-1111-1111-1111-111111111111",
                site_key="  ",
                type=EventType.pageview,
            ).to_payload(),
            client_ip="1.1.1.1",
            user_agent=None,
            origin="https://a.com",
            referer=None,
        )

    svc.sites.get_by_site_key = MagicMock(
        return_value={"id": uuid4(), "allowed_domains": ["", "  "], "name": "x", "site_key": "sk_x"}
    )
    with pytest.raises(ForbiddenError, match="no allowed domains"):
        svc.ingest(
            CollectEvent(
                event_id="11111111-1111-1111-1111-111111111111",
                site_key="sk_x",
                type=EventType.pageview,
            ).to_payload(),
            client_ip=None,
            user_agent=None,
            origin="https://a.com",
            referer=None,
        )


def test_collect_referer_and_invalid_event_id():
    with pytest.raises(ValidationError):
        CollectEvent(site_key="sk_x", type=EventType.pageview, event_id="bad")

    engine, _conn = _engine_with_conn()
    svc = CollectService(engine)
    svc.sites.get_by_site_key = MagicMock(
        return_value={
            "id": uuid4(),
            "allowed_domains": ["example.com"],
            "name": "x",
            "site_key": "sk_x",
        }
    )
    svc.events.insert = MagicMock(return_value=True)
    svc.ingest(
        CollectEvent(
            event_id="11111111-1111-1111-1111-111111111111",
            site_key="sk_x",
            type=EventType.pageview,
        ).to_payload(),
        client_ip="1.1.1.1",
        user_agent="ua",
        origin=None,
        referer="https://example.com/page",
    )
    svc.events.insert.assert_called_once()


def test_hash_password_and_seed_when_empty(monkeypatch):
    auth = AuthService()
    hashed = auth.hash_password("changeme123456")
    assert auth.verify_password("changeme123456", hashed)

    class FakeRepo:
        def count(self, _conn):
            return 0

        def insert(self, _conn, username, password_hash):
            self.inserted = (username, password_hash)
            return {"id": "1", "username": username}

    fake = FakeRepo()
    monkeypatch.setattr("db.migrations.UsersRepository", lambda: fake)
    monkeypatch.setattr("db.migrations.get_connection", lambda _engine: _ConnCtx())
    _seed_admin(MagicMock())
    assert fake.inserted[0]


def test_users_repository_insert_returns_row():
    from uuid import uuid4

    from db.repositories.users import UsersRepository

    user_id = uuid4()
    conn = MagicMock()
    result = MagicMock()
    result.mappings.return_value.one.return_value = {"id": user_id, "username": "admin"}
    conn.execute.return_value = result

    row = UsersRepository().insert(conn, "admin", "hash")
    assert row == {"id": user_id, "username": "admin"}
    conn.execute.assert_called_once()


def test_create_db_engine_pool_size_outside_test(monkeypatch):
    from sqlalchemy.pool import NullPool

    from db import connection

    monkeypatch.setattr(connection.settings, "app_env", "production")
    engine = connection.create_db_engine("sqlite+pysqlite:///:memory:")
    assert not isinstance(engine.pool, NullPool)
    engine.dispose()


class _ConnCtx:
    def __enter__(self):
        return MagicMock()

    def __exit__(self, *args):
        return False
