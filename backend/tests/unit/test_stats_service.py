"""Unit tests for stats aggregation logic."""

from datetime import UTC, date, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4
from zoneinfo import ZoneInfo

from services.stats import StatsService, resolve_tz


def _service_with_repo(repo: MagicMock) -> StatsService:
    service = StatsService()
    service.events = repo
    return service


def _patch_now(stats_module, fixed_now: datetime):
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return fixed_now.replace(tzinfo=None)
            return fixed_now.astimezone(tz)

    original = stats_module.datetime
    stats_module.datetime = FixedDatetime
    return original


def test_resolve_tz_falls_back_to_utc():
    assert str(resolve_tz(None)) == "UTC"
    assert str(resolve_tz("Not/AZone")) == "UTC"
    assert str(resolve_tz("America/Los_Angeles")) == "America/Los_Angeles"


def test_visits_totals_sum_event_counts():
    site_id = uuid4()
    repo = MagicMock()
    repo.visits_series.return_value = [
        {
            "day": date(2026, 7, 7),
            "pageviews": 10,
            "clicks": 2,
            "hovers": 3,
            "visitors": 4,
        },
        {
            "day": date(2026, 7, 8),
            "pageviews": 6,
            "clicks": 1,
            "hovers": 1,
            "visitors": 3,
        },
    ]
    repo.count_visitors.return_value = 5

    service = _service_with_repo(repo)
    fixed_now = datetime(2026, 7, 8, 15, 30, tzinfo=UTC)

    import services.stats as stats_module

    original_datetime = _patch_now(stats_module, fixed_now)
    try:
        result = service.visits(MagicMock(), site_id, days=2)
    finally:
        stats_module.datetime = original_datetime

    assert result["totals"]["pageviews"] == 16
    assert result["totals"]["clicks"] == 3
    assert result["totals"]["hovers"] == 4
    assert len(result["series"]) == 2


def test_visits_period_visitors_uses_distinct_count_not_daily_max():
    site_id = uuid4()
    repo = MagicMock()
    repo.visits_series.return_value = [
        {
            "day": date(2026, 7, 7),
            "pageviews": 5,
            "clicks": 0,
            "hovers": 0,
            "visitors": 5,
        },
        {
            "day": date(2026, 7, 8),
            "pageviews": 5,
            "clicks": 0,
            "hovers": 0,
            "visitors": 5,
        },
    ]
    repo.count_visitors.return_value = 8

    service = _service_with_repo(repo)
    fixed_now = datetime(2026, 7, 8, 12, 0, tzinfo=UTC)

    import services.stats as stats_module

    original_datetime = _patch_now(stats_module, fixed_now)
    try:
        result = service.visits(MagicMock(), site_id, days=2)
    finally:
        stats_module.datetime = original_datetime

    peak_daily = max(row["visitors"] for row in result["series"])
    assert result["totals"]["visitors"] == 8
    assert result["totals"]["visitors"] > peak_daily
    repo.count_visitors.assert_called_once()


def test_visits_hours_period_visitors_uses_distinct_count():
    site_id = uuid4()
    repo = MagicMock()
    hour = datetime(2026, 7, 8, 10, 0, tzinfo=UTC)
    repo.visits_series_hourly.return_value = [
        {
            "hour": hour,
            "pageviews": 3,
            "clicks": 1,
            "hovers": 0,
            "visitors": 2,
        }
    ]
    repo.count_visitors.return_value = 6

    service = _service_with_repo(repo)
    fixed_now = datetime(2026, 7, 8, 10, 30, tzinfo=UTC)

    import services.stats as stats_module

    original_datetime = _patch_now(stats_module, fixed_now)
    try:
        result = service.visits_hours(MagicMock(), site_id, hours=3)
    finally:
        stats_module.datetime = original_datetime

    assert result["totals"]["visitors"] == 6
    repo.count_visitors.assert_called_once()
    call_kwargs = repo.count_visitors.call_args.kwargs
    assert call_kwargs["start"] < call_kwargs["end"]
    assert call_kwargs["end"] == fixed_now


def test_visits_hours_accepts_naive_hour_rows():
    site_id = uuid4()
    repo = MagicMock()
    # Defensive path: some drivers may return naive timestamps.
    repo.visits_series_hourly.return_value = [
        {
            "hour": datetime(2026, 7, 8, 10, 0),
            "pageviews": 1,
            "clicks": 0,
            "hovers": 0,
            "visitors": 1,
        }
    ]
    repo.count_visitors.return_value = 1
    service = _service_with_repo(repo)
    fixed_now = datetime(2026, 7, 8, 10, 30, tzinfo=UTC)

    import services.stats as stats_module

    original_datetime = _patch_now(stats_module, fixed_now)
    try:
        result = service.visits_hours(MagicMock(), site_id, hours=1, tz_name="UTC")
    finally:
        stats_module.datetime = original_datetime

    assert result["series"][-1]["pageviews"] == 1


def test_visits_hours_uses_client_tz_buckets_and_snaps_end_to_now():
    site_id = uuid4()
    repo = MagicMock()
    repo.visits_series_hourly.return_value = []
    repo.count_visitors.return_value = 0

    # 2026-07-08 18:37 UTC == 11:37 America/Los_Angeles
    fixed_now = datetime(2026, 7, 8, 18, 37, tzinfo=UTC)
    service = _service_with_repo(repo)

    import services.stats as stats_module

    original_datetime = _patch_now(stats_module, fixed_now)
    try:
        result = service.visits_hours(
            MagicMock(), site_id, hours=24, tz_name="America/Los_Angeles"
        )
    finally:
        stats_module.datetime = original_datetime

    repo.visits_series_hourly.assert_called_once()
    call_kwargs = repo.visits_series_hourly.call_args.kwargs
    assert call_kwargs["tz"] == "America/Los_Angeles"
    assert call_kwargs["end"] == fixed_now
    assert call_kwargs["start"] == fixed_now - timedelta(hours=24)

    # Local hours from 11:00 yesterday through 11:00 today inclusive.
    assert len(result["series"]) == 25
    first = datetime.fromisoformat(result["series"][0]["date"].replace("Z", "+00:00"))
    last = datetime.fromisoformat(result["series"][-1]["date"].replace("Z", "+00:00"))
    la = ZoneInfo("America/Los_Angeles")
    assert first.astimezone(la).hour == 11
    assert last.astimezone(la).hour == 11
    assert last.astimezone(la).date() == fixed_now.astimezone(la).date()
