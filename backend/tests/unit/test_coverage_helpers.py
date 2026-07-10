"""Unit tests for pure helpers and service edge cases."""

from __future__ import annotations

import logging
import sys

import pytest
from pydantic import ValidationError

from app.api.routers.partials import _format_location, _format_time
from app.api.schemas import CollectEvent
from config.logging import JsonFormatter, setup_logging
from core.exceptions import NotFoundError, UnauthorizedError
from core.rate_limit import SlidingWindowRateLimiter
from demo import fixtures as demo_fixtures
from demo import mode as demo_mode
from services.auth import AuthService
from services.sites import SitesService


def test_format_time_invalid_falls_back():
    assert _format_time("not-a-date") == "not-a-date"


def test_format_location_variants():
    assert _format_location({"city": "Austin", "country": "US"}) == "Austin, US"
    assert _format_location({"country": "US"}) == "US"
    assert _format_location({}) == "-"


def test_collect_event_id_must_be_uuid():
    with pytest.raises(ValidationError):
        CollectEvent(event_id="not-a-uuid", site_key="sk_x", type="pageview")


def test_json_formatter_includes_exc_info():
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="t",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="boom",
        args=(),
        exc_info=None,
    )
    try:
        raise RuntimeError("x")
    except RuntimeError:
        record.exc_info = sys.exc_info()
    payload = formatter.format(record)
    assert "boom" in payload
    assert "exc_info" in payload


def test_setup_logging_sets_handler():
    setup_logging()
    root = logging.getLogger()
    assert root.handlers
    assert isinstance(root.handlers[0].formatter, JsonFormatter)


def test_not_found_default_message():
    err = NotFoundError()
    assert err.status_code == 404
    assert err.message == "Not found"


def test_rate_limiter_prunes_when_over_max_keys(monkeypatch):
    limiter = SlidingWindowRateLimiter(max_keys=1)
    assert limiter.allow("a", limit=10, window_sec=0.0)
    # Stale key "a" (window_sec=0) should be pruned when adding "b".
    assert limiter.allow("b", limit=10, window_sec=0.0)


def test_auth_decode_token_errors():
    auth = AuthService()
    with pytest.raises(UnauthorizedError):
        auth.decode_token("not-a-jwt")
    assert auth.decode_token_optional("not-a-jwt") is None


def test_sites_normalize_errors():
    svc = SitesService()
    with pytest.raises(Exception):
        svc._normalize_domains([])
    with pytest.raises(Exception):
        svc._normalize_site_key("bad")


def test_demo_mode_cookie_branches(monkeypatch):
    class Req:
        def __init__(self, cookies):
            self.cookies = cookies

    monkeypatch.setattr(demo_mode.settings, "app_env", "test")
    assert demo_mode.enabled_from_request(Req({demo_mode.COOKIE_NAME: "1"})) is True
    assert demo_mode.enabled_from_request(Req({demo_mode.COOKIE_NAME: "0"})) is False
    assert demo_mode.enabled_from_request(Req({demo_mode.COOKIE_NAME: "weird"})) is False

    monkeypatch.setattr(demo_mode.settings, "app_env", "production")
    assert demo_mode.enabled_from_request(Req({})) is False


def test_demo_visitor_set_zero_count():
    assert demo_fixtures._visitor_set(count=0, day_index=0, previous=set()) == set()


def test_demo_list_events_filters_and_sort():
    data = demo_fixtures.list_events(
        demo_fixtures.DEMO_SITE_ID,
        event_type="click",
        q="cta",
        sort="path",
        order="asc",
        page=1,
        limit=5,
    )
    assert data["page"] == 1
    assert all(item["type"] == "click" for item in data["items"])
