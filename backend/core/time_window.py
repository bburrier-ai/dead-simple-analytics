"""Shared dashboard period window helpers."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def resolve_tz(name: str | None) -> ZoneInfo:
    if not name:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def period_bounds(
    *,
    days: int | None = None,
    hours: int | None = None,
    tz_name: str | None = None,
) -> tuple[datetime, datetime] | None:
    """Return UTC [start, end) matching the dashboard chart period, or None if unset."""
    if hours is not None:
        end = datetime.now(UTC)
        start = end - timedelta(hours=max(1, hours))
        return start, end
    if days is not None:
        tz = resolve_tz(tz_name)
        end_local = datetime.now(tz).date()
        start_local = end_local - timedelta(days=max(1, days) - 1)
        start = datetime.combine(start_local, datetime.min.time(), tz).astimezone(UTC)
        end = datetime.combine(
            end_local + timedelta(days=1), datetime.min.time(), tz
        ).astimezone(UTC)
        return start, end
    return None
