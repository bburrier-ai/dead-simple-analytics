"""Unit tests for visitor_hash normalization."""

from services.collect import CollectService


def test_normalize_visitor_hash_accepts_sha256_hex():
    service = CollectService()
    raw = "a" * 64
    assert service._normalize_visitor_hash(raw) == raw


def test_normalize_visitor_hash_accepts_fallback_prefix():
    service = CollectService()
    raw = "f_deadbeef"
    assert service._normalize_visitor_hash(raw) == raw


def test_normalize_visitor_hash_rejects_invalid_values():
    service = CollectService()
    assert service._normalize_visitor_hash("not-a-hash") is None
    assert service._normalize_visitor_hash("") is None
    assert service._normalize_visitor_hash(None) is None
