"""Unit tests for stats aggregation logic."""

from datetime import UTC, date, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from services.stats import StatsService


def _service_with_repo(repo: MagicMock) -> StatsService:
    service = StatsService()
    service.events = repo
    return service


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

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    import services.stats as stats_module

    original_datetime = stats_module.datetime
    stats_module.datetime = FixedDatetime
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

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    import services.stats as stats_module

    original_datetime = stats_module.datetime
    stats_module.datetime = FixedDatetime
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

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now if tz else fixed_now.replace(tzinfo=None)

    import services.stats as stats_module

    original_datetime = stats_module.datetime
    stats_module.datetime = FixedDatetime
    try:
        result = service.visits_hours(MagicMock(), site_id, hours=3)
    finally:
        stats_module.datetime = original_datetime

    assert result["totals"]["visitors"] == 6
    repo.count_visitors.assert_called_once()
    call_kwargs = repo.count_visitors.call_args.kwargs
    assert call_kwargs["start"] < call_kwargs["end"]
