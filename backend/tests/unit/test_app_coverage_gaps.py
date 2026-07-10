import json
import logging
import sys
from collections import defaultdict
from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.routers.partials import _format_time
from app.api.schemas import CollectEvent
from config.logging import JsonFormatter
from core.exceptions import NotFoundError
from core.rate_limit import SlidingWindowRateLimiter
from db.repositories.events import EventsRepository
from db.repositories.sites import SitesRepository
from demo import fixtures as demo_fixtures
from demo import mode as demo_mode
from services.auth import AuthService
from services.collect import CollectService
from services.sites import SitesService


def test_collect_event_rejects_non_uuid_event_id():
    with pytest.raises(ValidationError) as exc_info:
        CollectEvent(event_id="x" * 36, site_key="sk_test", type="pageview")

    assert "event_id must be a UUID" in str(exc_info.value)


def test_format_time_escapes_invalid_iso_value():
    assert _format_time("<not-a-date>") == "&lt;not-a-date&gt;"


def test_json_formatter_includes_exception_info():
    formatter = JsonFormatter()
    logger = logging.getLogger("test-json-formatter")

    try:
        raise RuntimeError("boom")
    except RuntimeError:
        record = logger.makeRecord(
            "test-json-formatter",
            logging.ERROR,
            __file__,
            1,
            "failed %s",
            ("hard",),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(formatter.format(record))
    assert payload["message"] == "failed hard"
    assert "RuntimeError: boom" in payload["exc_info"]


def test_not_found_error_sets_status_code():
    exc = NotFoundError()
    assert exc.message == "Not found"
    assert exc.status_code == 404


def test_rate_limiter_prunes_stale_keys_when_over_capacity():
    limiter = SlidingWindowRateLimiter(max_keys=1)
    limiter._buckets = defaultdict(list, {"stale": [10.0], "empty": [], "fresh": [100.0]})

    limiter._maybe_prune(now=100.0, window_sec=60.0)

    assert "stale" not in limiter._buckets
    assert "empty" not in limiter._buckets
    assert "fresh" in limiter._buckets


def test_auth_decode_token_error_paths():
    service = AuthService()

    with pytest.raises(Exception) as exc_info:
        service.decode_token("not-a-token")

    assert "Invalid session" in str(exc_info.value)
    assert service.decode_token_optional("not-a-token") is None


def test_collect_service_direct_error_paths():
    service = CollectService()
    conn = MagicMock()
    site = {
        "id": uuid4(),
        "site_key": "sk_test",
        "allowed_domains": ["example.com"],
    }
    service.sites.get_by_site_key = MagicMock(return_value=site)
    service.events.insert = MagicMock(return_value=True)

    with pytest.raises(Exception) as exc_info:
        service.ingest(
            conn,
            {"site_key": "sk_test", "type": "pageview", "event_id": "bad"},
            client_ip="127.0.0.1",
            user_agent=None,
            origin="https://example.com",
            referer=None,
        )
    assert "Invalid event_id" in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        service._check_origin(["example.com"], None, None)
    assert "Missing Origin/Referer" in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        service._check_origin([], "https://example.com", None)
    assert "Site has no allowed domains" in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        service._check_origin(["example.com"], "https://evil.test", None)
    assert "Origin not allowed" in str(exc_info.value)

    assert service._host_from_header(None) is None
    assert service._normalize_visitor_hash("F_" + "A" * 10) == "f_" + "a" * 10
    assert service._normalize_visitor_hash("not valid!") is None


def test_sites_service_error_and_lookup_paths():
    service = SitesService()
    conn = MagicMock()
    user_id = uuid4()
    site_id = uuid4()
    service.repo = MagicMock()

    service.repo.site_key_in_use.return_value = False
    service.repo.update.return_value = None
    with pytest.raises(Exception) as exc_info:
        service.update_site(conn, user_id, site_id, "Missing", ["example.com"], "sk_missing")
    assert "Site not found" in str(exc_info.value)

    service.repo.get_by_id.return_value = None
    with pytest.raises(Exception) as exc_info:
        service.get_site(conn, user_id, site_id)
    assert "Site not found" in str(exc_info.value)

    service.repo.get_by_id.return_value = {
        "id": site_id,
        "name": "Found",
        "site_key": "sk_found",
        "allowed_domains": ["example.com"],
    }
    found = service.get_site(conn, user_id, site_id)
    assert found["snippet"].endswith('data-site="sk_found"></script>')

    with pytest.raises(Exception) as exc_info:
        service.create_site(conn, user_id, "No domains", ["", " "])
    assert "At least one allowed domain" in str(exc_info.value)

    with pytest.raises(Exception) as exc_info:
        service.update_site(conn, user_id, site_id, "Bad key", ["example.com"], "bad-key")
    assert "Site key must start with sk_" in str(exc_info.value)


def test_events_repository_builds_filter_search_and_sort_queries():
    conn = MagicMock()
    conn.execute.side_effect = [
        MagicMock(scalar_one=MagicMock(return_value=1)),
        MagicMock(
            mappings=MagicMock(
                return_value=[
                    {
                        "id": uuid4(),
                        "type": "click",
                        "path": "/buy",
                        "occurred_at": datetime(2026, 7, 8, tzinfo=UTC),
                    }
                ]
            )
        ),
    ]

    rows, total = EventsRepository().list_events(
        conn,
        uuid4(),
        event_type="click",
        q="buy",
        sort="path",
        order="asc",
        page=2,
        limit=10,
    )

    assert total == 1
    assert rows[0]["path"] == "/buy"
    count_sql = str(conn.execute.call_args_list[0].args[0])
    rows_sql = str(conn.execute.call_args_list[1].args[0])
    params = conn.execute.call_args_list[0].args[1]
    assert "type = :event_type" in count_sql
    assert "ILIKE :q" in count_sql
    assert "ORDER BY path ASC" in rows_sql
    assert params["q"] == "%buy%"
    assert params["offset"] == 10


def test_events_repository_defaults_invalid_sort_and_desc_order():
    conn = MagicMock()
    conn.execute.side_effect = [
        MagicMock(scalar_one=MagicMock(return_value=0)),
        MagicMock(mappings=MagicMock(return_value=[])),
    ]

    rows, total = EventsRepository().list_events(
        conn,
        uuid4(),
        event_type="all",
        sort="not_allowed",
        order="sideways",
        page=0,
        limit=25,
    )

    assert rows == []
    assert total == 0
    params = conn.execute.call_args_list[0].args[1]
    rows_sql = str(conn.execute.call_args_list[1].args[0])
    assert params["offset"] == 0
    assert "ORDER BY occurred_at DESC" in rows_sql


def test_sites_repository_get_by_id_found_and_missing():
    row = {
        "id": uuid4(),
        "name": "Site",
        "site_key": "sk_site",
        "allowed_domains": ["example.com"],
        "active": True,
    }
    conn = MagicMock()
    conn.execute.return_value.mappings.return_value.first.return_value = row

    assert SitesRepository().get_by_id(conn, row["id"], uuid4()) == row

    conn.execute.return_value.mappings.return_value.first.return_value = None
    assert SitesRepository().get_by_id(conn, uuid4(), uuid4()) is None


def test_demo_fixture_edge_branches():
    assert demo_fixtures._visitor_set(count=0, day_index=0, previous={"demo_v_0001"}) == set()

    clicked = demo_fixtures.list_events(
        demo_fixtures.DEMO_SITE_ID,
        event_type="click",
        q="CTA",
        sort="type",
        order="asc",
        limit=2,
    )
    assert clicked["total"] >= 1
    assert all(row["type"] == "click" for row in clicked["items"])

    by_time = demo_fixtures.list_events(
        demo_fixtures.DEMO_SITE_ID,
        sort="occurred_at",
        order="desc",
        limit=1,
    )
    assert by_time["items"][0]["occurred_at"].endswith("Z")


def test_demo_mode_cookie_branches():
    request = MagicMock()
    request.cookies = {demo_mode.COOKIE_NAME: demo_mode.COOKIE_ENABLED}
    assert demo_mode.enabled_from_request(request, environment="test") is True

    request.cookies = {demo_mode.COOKIE_NAME: demo_mode.COOKIE_DISABLED}
    assert demo_mode.enabled_from_request(request, environment="test") is False

    request.cookies = {demo_mode.COOKIE_NAME: "unexpected"}
    assert demo_mode.enabled_from_request(request, environment="local") is True
    assert demo_mode.enabled_from_request(request, environment="production") is False

