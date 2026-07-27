"""Unit tests for track_id allowlist normalization."""

from services.collect import CollectService


def test_normalize_track_id_accepts_safe_slugs():
    service = CollectService()
    for value in (
        "newsletter",
        "cta-signup",
        "spring_sale",
        "campaign:v2",
        "a",
        "A1.b2_c3-d4:e5",
        "x" * 128,
    ):
        assert service._normalize_track_id(value) == value


def test_normalize_track_id_rejects_injection_payloads():
    service = CollectService()
    for value in (
        None,
        "",
        "   ",
        "<script>alert(1)</script>",
        "'; DROP TABLE events;--",
        "' OR '1'='1",
        'cta"onclick=alert(1)',
        "javascript:alert(1)",
        "../../etc/passwd",
        "has space",
        "-leading-dash",
        ".leading-dot",
        "emoji-🔥",
        "newline\ninjection",
        "null\x00byte",
    ):
        assert service._normalize_track_id(value) is None


def test_normalize_track_id_clips_then_validates():
    service = CollectService()
    assert service._normalize_track_id("a" * 200) == "a" * 128
    # Clip can leave a trailing metacharacter that still fails the allowlist.
    assert service._normalize_track_id("ok" + ("<" * 200)) is None
