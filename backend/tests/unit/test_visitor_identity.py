"""Unit tests for visitor identity SQL expression."""

from db.repositories.events import VISITOR_IDENTITY_SQL


def test_visitor_identity_prefers_hash_over_id():
    assert "visitor_hash" in VISITOR_IDENTITY_SQL
    assert "visitor_id" in VISITOR_IDENTITY_SQL
    assert VISITOR_IDENTITY_SQL.index("visitor_hash") < VISITOR_IDENTITY_SQL.index("visitor_id")
