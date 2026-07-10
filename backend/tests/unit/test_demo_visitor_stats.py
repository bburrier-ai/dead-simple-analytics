"""Unit tests for demo fixture visitor calculations."""

from demo import fixtures as demo_fixtures


def test_demo_daily_visitor_sets_match_declared_counts():
    for row in demo_fixtures._CHART_SERIES:
        visitor_set = demo_fixtures._DAILY_VISITOR_SETS[row["date"]]
        assert len(visitor_set) == row["visitors"]


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
