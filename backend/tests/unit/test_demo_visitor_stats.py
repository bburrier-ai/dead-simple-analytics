"""Unit tests for demo fixture visitor calculations."""

from demo import fixtures as demo_fixtures


def test_demo_list_events_and_chart_helpers():
    assert demo_fixtures._CHART_SERIES
    assert demo_fixtures._DAILY_VISITOR_SETS
    assert demo_fixtures._EVENTS
    try:
        _ = demo_fixtures._no_such_attr
        raise AssertionError("expected AttributeError")
    except AttributeError:
        pass

    series = demo_fixtures.chart_series(days=30, tz_name="UTC")
    assert len(series) == 30
    assert demo_fixtures.daily_visitor_sets(series)

    clicks = demo_fixtures.list_events(
        demo_fixtures.DEMO_SITE_ID,
        event_type="click",
        q="cta",
        sort="path",
        order="asc",
        page=1,
        limit=5,
    )
    assert clicks["page"] == 1
    assert all(item["type"] == "click" for item in clicks["items"])

    hours = demo_fixtures.visits_stats(hours=24, tz_name="UTC")
    assert hours["totals"]["pageviews"] >= 0
    assert len(hours["series"]) >= 1


def test_demo_visits_stats_matches_selected_day_range():
    for days in (7, 14, 30, 90):
        stats = demo_fixtures.visits_stats(days=days, tz_name="America/Los_Angeles")
        assert len(stats["series"]) == days
        assert stats["series"][-1]["date"] == demo_fixtures.chart_series(
            days=1, tz_name="America/Los_Angeles"
        )[0]["date"]


def test_demo_14_day_period_visitors_exceeds_peak_daily():
    stats = demo_fixtures.visits_stats(days=14)
    peak_daily = max(row["visitors"] for row in stats["series"])
    assert stats["totals"]["visitors"] > peak_daily


def test_demo_7_day_period_visitors_is_union_not_sum():
    stats = demo_fixtures.visits_stats(days=7)
    peak_daily = max(row["visitors"] for row in stats["series"])
    summed_daily = sum(row["visitors"] for row in stats["series"])
    total = stats["totals"]["visitors"]

    assert total > peak_daily
    assert total < summed_daily


def test_demo_24_hour_period_visitors_exceeds_peak_hour():
    stats = demo_fixtures.visits_stats(hours=24)
    assert len(stats["series"]) >= 24
    peak_hourly = max(row["visitors"] for row in stats["series"])
    assert stats["totals"]["visitors"] > peak_hourly


def test_union_visitor_count_deduplicates_across_slices():
    sets = [
        {"a", "b", "c"},
        {"b", "c", "d"},
        {"d", "e"},
    ]
    assert demo_fixtures._union_visitor_count(sets) == 5


def test_visitor_set_respects_target_count():
    first = demo_fixtures._visitor_set(count=10, day_index=0, previous=set())
    second = demo_fixtures._visitor_set(count=12, day_index=1, previous=first)

    assert len(first) == 10
    assert len(second) == 12
    assert first & second  # overlap across adjacent slices
