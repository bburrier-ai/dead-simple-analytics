from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.engine import Connection

from db.repositories.events import EventsRepository


def resolve_tz(name: str | None) -> ZoneInfo:
    if not name:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


class StatsService:
    def __init__(self) -> None:
        self.events = EventsRepository()

    def visits(
        self,
        conn: Connection,
        site_id: UUID,
        *,
        days: int = 14,
        tz_name: str | None = None,
    ) -> dict:
        tz = resolve_tz(tz_name)
        end_local = datetime.now(tz).date()
        start_local = end_local - timedelta(days=max(1, days) - 1)
        start_dt = datetime.combine(start_local, datetime.min.time(), tz)
        end_dt = datetime.combine(end_local + timedelta(days=1), datetime.min.time(), tz)
        rows = self.events.visits_series(
            conn,
            site_id,
            date_from=start_local.isoformat(),
            date_to=end_local.isoformat(),
            tz=str(tz),
        )
        by_day = {str(r["day"]): r for r in rows}
        series = []
        cursor = start_local
        while cursor <= end_local:
            key = cursor.isoformat()
            row = by_day.get(key, {})
            series.append(
                {
                    "date": key,
                    "pageviews": int(row.get("pageviews") or 0),
                    "clicks": int(row.get("clicks") or 0),
                    "hovers": int(row.get("hovers") or 0),
                    "visitors": int(row.get("visitors") or 0),
                }
            )
            cursor += timedelta(days=1)

        totals = {
            "pageviews": sum(s["pageviews"] for s in series),
            "clicks": sum(s["clicks"] for s in series),
            "hovers": sum(s["hovers"] for s in series),
            "visitors": self.events.count_visitors(
                conn, site_id, start=start_dt.astimezone(UTC), end=end_dt.astimezone(UTC)
            ),
        }
        return {"series": series, "totals": totals}

    def visits_hours(
        self,
        conn: Connection,
        site_id: UUID,
        *,
        hours: int = 24,
        tz_name: str | None = None,
    ) -> dict:
        tz = resolve_tz(tz_name)
        # Rolling window ending at now (not floored to the hour).
        end = datetime.now(UTC)
        start = end - timedelta(hours=max(1, hours))
        rows = self.events.visits_series_hourly(
            conn, site_id, start=start, end=end, tz=str(tz)
        )
        by_hour: dict[datetime, dict] = {}
        for row in rows:
            hour = row["hour"]
            if hour.tzinfo is None:
                hour = hour.replace(tzinfo=UTC)
            by_hour[hour.astimezone(UTC)] = row

        start_local = start.astimezone(tz)
        end_local = end.astimezone(tz)
        # Local hour buckets that intersect [start, end], including the current partial hour.
        cursor = start_local.replace(minute=0, second=0, microsecond=0)

        series = []
        while cursor <= end_local:
            hour_utc = cursor.astimezone(UTC)
            row = by_hour.get(hour_utc, {})
            series.append(
                {
                    "date": hour_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "pageviews": int(row.get("pageviews") or 0),
                    "clicks": int(row.get("clicks") or 0),
                    "hovers": int(row.get("hovers") or 0),
                    "visitors": int(row.get("visitors") or 0),
                }
            )
            cursor += timedelta(hours=1)

        totals = {
            "pageviews": sum(s["pageviews"] for s in series),
            "clicks": sum(s["clicks"] for s in series),
            "hovers": sum(s["hovers"] for s in series),
            "visitors": self.events.count_visitors(conn, site_id, start=start, end=end),
        }
        return {"series": series, "totals": totals}
