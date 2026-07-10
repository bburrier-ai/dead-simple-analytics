"""Unit tests for remaining service / migration edges."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.exceptions import ForbiddenError
from db.migrations import _seed_admin
from services.auth import AuthService
from services.collect import CollectService


def test_collect_missing_site_key_and_empty_domains():
    svc = CollectService()
    conn = MagicMock()
    with pytest.raises(ForbiddenError, match="Missing site_key"):
        svc.ingest(
            conn,
            {"site_key": ""},
            client_ip="1.1.1.1",
            user_agent=None,
            origin="https://a.com",
            referer=None,
        )

    svc.sites.get_by_site_key = MagicMock(
        return_value={"id": "x", "allowed_domains": ["", "  "]}
    )
    with pytest.raises(ForbiddenError, match="no allowed domains"):
        svc.ingest(
            conn,
            {
                "site_key": "sk_x",
                "type": "pageview",
                "event_id": "11111111-1111-1111-1111-111111111111",
            },
            client_ip=None,
            user_agent=None,
            origin="https://a.com",
            referer=None,
        )


def test_collect_referer_and_invalid_event_id():
    svc = CollectService()
    conn = MagicMock()
    svc.sites.get_by_site_key = MagicMock(
        return_value={"id": "x", "allowed_domains": ["example.com"]}
    )
    with pytest.raises(ForbiddenError, match="Invalid event_id"):
        svc.ingest(
            conn,
            {"site_key": "sk_x", "type": "pageview", "event_id": "bad"},
            client_ip="1.1.1.1",
            user_agent="ua",
            origin=None,
            referer="https://example.com/page",
        )


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
    monkeypatch.setattr("db.migrations.get_connection", lambda: _ConnCtx())
    _seed_admin()
    assert fake.inserted[0]


def test_get_engine_pool_size_outside_test(monkeypatch):
    from sqlalchemy.pool import NullPool

    from db import connection

    monkeypatch.setattr(connection.settings, "app_env", "production")
    connection._engine = None
    engine = connection.get_engine("sqlite+pysqlite:///:memory:")
    assert not isinstance(engine.pool, NullPool)
    connection._engine = None


class _ConnCtx:
    def __enter__(self):
        return MagicMock()

    def __exit__(self, *args):
        return False
