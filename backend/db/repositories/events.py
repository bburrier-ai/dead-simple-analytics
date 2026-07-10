from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

# Prefer fingerprint hash; fall back to first-party visitor_id.
VISITOR_IDENTITY_SQL = (
    "COALESCE(NULLIF(visitor_hash, ''), NULLIF(visitor_id, ''))"
)


class EventsRepository:
    def insert(self, conn: Connection, event: dict) -> bool:
        row = conn.execute(
            text(
                """
                INSERT INTO events (
                    site_id, event_id, type, path, title, track_id, referrer,
                    visitor_id, visitor_hash, session_id, ip_hash,
                    country, region, city, user_agent
                ) VALUES (
                    :site_id, :event_id, :type, :path, :title, :track_id, :referrer,
                    :visitor_id, :visitor_hash, :session_id, :ip_hash,
                    :country, :region, :city, :user_agent
                )
                ON CONFLICT (site_id, event_id) WHERE event_id IS NOT NULL DO NOTHING
                RETURNING id
                """
            ),
            event,
        ).first()
        return row is not None

    def list_events(
        self,
        conn: Connection,
        site_id: UUID,
        *,
        event_type: str | None = None,
        q: str | None = None,
        sort: str = "occurred_at",
        order: str = "desc",
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[dict], int]:
        allowed_sort = {
            "occurred_at",
            "type",
            "path",
            "track_id",
            "referrer",
            "city",
            "session_id",
        }
        sort_col = sort if sort in allowed_sort else "occurred_at"
        order_sql = "ASC" if order.lower() == "asc" else "DESC"
        offset = max(0, (page - 1) * limit)

        filters = ["site_id = :site_id"]
        params: dict = {"site_id": site_id, "limit": limit, "offset": offset}

        if event_type and event_type != "all":
            filters.append("type = :event_type")
            params["event_type"] = event_type

        if q:
            filters.append(
                """
                (
                    path ILIKE :q OR COALESCE(track_id, '') ILIKE :q OR
                    COALESCE(referrer, '') ILIKE :q OR COALESCE(visitor_id, '') ILIKE :q OR
                    COALESCE(visitor_hash, '') ILIKE :q OR
                    COALESCE(session_id, '') ILIKE :q OR COALESCE(city, '') ILIKE :q
                )
                """
            )
            params["q"] = f"%{q}%"

        where = " AND ".join(filters)
        count_row = conn.execute(
            text(f"SELECT COUNT(*) FROM events WHERE {where}"),
            params,
        ).scalar_one()

        rows = conn.execute(
            text(
                f"""
                SELECT id, type, path, title, track_id, referrer, visitor_id, visitor_hash,
                       session_id, country, region, city, occurred_at
                FROM events
                WHERE {where}
                ORDER BY {sort_col} {order_sql}
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).mappings()
        return [dict(r) for r in rows], int(count_row)

    def count_visitors(
        self,
        conn: Connection,
        site_id: UUID,
        *,
        start: datetime,
        end: datetime,
    ) -> int:
        total = conn.execute(
            text(
                f"""
                SELECT COUNT(DISTINCT {VISITOR_IDENTITY_SQL})
                FROM events
                WHERE site_id = :site_id
                  AND {VISITOR_IDENTITY_SQL} IS NOT NULL
                  AND occurred_at >= :start
                  AND occurred_at < :end
                """
            ),
            {"site_id": site_id, "start": start, "end": end},
        ).scalar_one()
        return int(total or 0)

    def visits_series_hourly(
        self,
        conn: Connection,
        site_id: UUID,
        *,
        start: datetime,
        end: datetime,
        tz: str = "UTC",
    ) -> list[dict]:
        rows = conn.execute(
            text(
                f"""
                SELECT
                    date_trunc('hour', occurred_at AT TIME ZONE :tz) AT TIME ZONE :tz AS hour,
                    COUNT(*) FILTER (WHERE type = 'pageview') AS pageviews,
                    COUNT(*) FILTER (WHERE type = 'click') AS clicks,
                    COUNT(*) FILTER (WHERE type = 'hover') AS hovers,
                    COUNT(DISTINCT {VISITOR_IDENTITY_SQL})
                        FILTER (WHERE {VISITOR_IDENTITY_SQL} IS NOT NULL) AS visitors
                FROM events
                WHERE site_id = :site_id
                  AND occurred_at >= :start
                  AND occurred_at < :end
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"site_id": site_id, "start": start, "end": end, "tz": tz},
        ).mappings()
        return [dict(r) for r in rows]

    def visits_series(
        self,
        conn: Connection,
        site_id: UUID,
        *,
        date_from: str,
        date_to: str,
        tz: str = "UTC",
    ) -> list[dict]:
        rows = conn.execute(
            text(
                f"""
                SELECT
                    date_trunc('day', occurred_at AT TIME ZONE :tz)::date AS day,
                    COUNT(*) FILTER (WHERE type = 'pageview') AS pageviews,
                    COUNT(*) FILTER (WHERE type = 'click') AS clicks,
                    COUNT(*) FILTER (WHERE type = 'hover') AS hovers,
                    COUNT(DISTINCT {VISITOR_IDENTITY_SQL})
                        FILTER (WHERE {VISITOR_IDENTITY_SQL} IS NOT NULL) AS visitors
                FROM events
                WHERE site_id = :site_id
                  AND occurred_at >= CAST(:date_from AS timestamp) AT TIME ZONE :tz
                  AND occurred_at < (CAST(:date_to AS date) + 1)::timestamp AT TIME ZONE :tz
                GROUP BY 1
                ORDER BY 1
                """
            ),
            {"site_id": site_id, "date_from": date_from, "date_to": date_to, "tz": tz},
        ).mappings()
        return [dict(r) for r in rows]
