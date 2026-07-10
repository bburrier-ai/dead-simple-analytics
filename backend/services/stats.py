from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.engine import Connection

from db.repositories.events import EventsRepository


class StatsService:
    def __init__(self) -> None:
        self.events = EventsRepository()

    def visits(
        self,
        conn: Connection,
        site_id: UUID,
        *,
        days: int = 14,
    ) -> dict:
        end = datetime.now(UTC).date()
        start = end - timedelta(days=max(1, days) - 1)
        start_dt = datetime.combine(start, datetime.min.time(), UTC)
        end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time(), UTC)
        rows = self.events.visits_series(
            conn,
            site_id,
            date_from=start.isoformat(),
            date_to=end.isoformat(),
        )
        by_day = {str(r["day"]): r for r in rows}
        series = []
        cursor = start
        while cursor <= end:
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
            "visitors": self.events.count_visitors(conn, site_id, start=start_dt, end=end_dt),
        }
        return {"series": series, "totals": totals}

    def visits_hours(
        self,
        conn: Connection,
        site_id: UUID,
        *,
        hours: int = 24,
    ) -> dict:
        end = datetime.now(UTC)
        start = end - timedelta(hours=max(1, hours))
        rows = self.events.visits_series_hourly(conn, site_id, start=start, end=end)
        by_hour = {r["hour"]: r for r in rows}

        cursor = start.replace(minute=0, second=0, microsecond=0)
        if cursor < start:
            cursor += timedelta(hours=1)

        series = []
        while cursor <= end:
            row = by_hour.get(cursor, {})
            series.append(
                {
                    "date": cursor.strftime("%Y-%m-%dT%H:%M:%SZ"),
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
