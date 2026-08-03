"""Event persistence queries.

S608 (SQL construction) is ignored for this module: dynamic fragments are
allowlisted identifiers / fixed predicates, and all user values are bound
parameters (:site_id, :q, …), never interpolated into SQL text.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Connection

# Prefer fingerprint hash; fall back to first-party visitor_id.
# Inlined into static SQL below (no f-string interpolation).
VISITOR_IDENTITY_SQL = "COALESCE(NULLIF(visitor_hash, ''), NULLIF(visitor_id, ''))"

_COUNT_VISITORS_SQL = text(
    """
    SELECT COUNT(DISTINCT COALESCE(NULLIF(visitor_hash, ''), NULLIF(visitor_id, '')))
    FROM events
    WHERE site_id = :site_id
      AND COALESCE(NULLIF(visitor_hash, ''), NULLIF(visitor_id, '')) IS NOT NULL
      AND occurred_at >= :start
      AND occurred_at < :end
    """
)

_VISITS_SERIES_HOURLY_SQL = text(
    """
    SELECT
        date_trunc('hour', occurred_at AT TIME ZONE :tz) AT TIME ZONE :tz AS hour,
        COUNT(*) FILTER (WHERE type = 'pageview') AS pageviews,
        COUNT(*) FILTER (WHERE type = 'click') AS clicks,
        COUNT(*) FILTER (WHERE type = 'hover') AS hovers,
        COUNT(DISTINCT COALESCE(NULLIF(visitor_hash, ''), NULLIF(visitor_id, '')))
            FILTER (
                WHERE COALESCE(NULLIF(visitor_hash, ''), NULLIF(visitor_id, ''))
                IS NOT NULL
            ) AS visitors
    FROM events
    WHERE site_id = :site_id
      AND occurred_at >= :start
      AND occurred_at < :end
    GROUP BY 1
    ORDER BY 1
    """
)

_VISITS_SERIES_DAILY_SQL = text(
    """
    SELECT
        date_trunc('day', occurred_at AT TIME ZONE :tz)::date AS day,
        COUNT(*) FILTER (WHERE type = 'pageview') AS pageviews,
        COUNT(*) FILTER (WHERE type = 'click') AS clicks,
        COUNT(*) FILTER (WHERE type = 'hover') AS hovers,
        COUNT(DISTINCT COALESCE(NULLIF(visitor_hash, ''), NULLIF(visitor_id, '')))
            FILTER (
                WHERE COALESCE(NULLIF(visitor_hash, ''), NULLIF(visitor_id, ''))
                IS NOT NULL
            ) AS visitors
    FROM events
    WHERE site_id = :site_id
      AND occurred_at >= CAST(:date_from AS timestamp) AT TIME ZONE :tz
      AND occurred_at < (CAST(:date_to AS date) + 1)::timestamp AT TIME ZONE :tz
    GROUP BY 1
    ORDER BY 1
    """
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
        start: datetime | None = None,
        end: datetime | None = None,
    ) -> tuple[list[dict], int]:
        allowed_sort = {
            "occurred_at",
            "type",
            "path",
            "track_id",
            "referrer",
            "city",
            "session_id",
            "visitor_id",
            "visitor_hash",
        }
        sort_col = sort if sort in allowed_sort else "occurred_at"
        order_sql = "ASC" if order.lower() == "asc" else "DESC"
        offset = max(0, (page - 1) * limit)

        filters = ["site_id = :site_id"]
        params: dict = {"site_id": site_id, "limit": limit, "offset": offset}

        if event_type and event_type != "all":
            filters.append("type = :event_type")
            params["event_type"] = event_type

        if start is not None and end is not None:
            filters.append("occurred_at >= :start AND occurred_at < :end")
            params["start"] = start
            params["end"] = end

        if q:
            filters.append(
                """
                (
                    path ILIKE :q OR COALESCE(track_id, '') ILIKE :q OR
                    COALESCE(referrer, '') ILIKE :q OR COALESCE(visitor_id, '') ILIKE :q OR
                    COALESCE(visitor_hash, '') ILIKE :q OR
                    COALESCE(session_id, '') ILIKE :q OR COALESCE(city, '') ILIKE :q OR
                    COALESCE(country, '') ILIKE :q
                )
                """
            )
            params["q"] = f"%{q}%"

        # WHERE predicates are fixed strings; ORDER BY uses an allowlisted column
        # name and ASC/DESC only. User values are bind params, not interpolated.
        where = " AND ".join(filters)
        count_sql = "SELECT COUNT(*) FROM events WHERE " + where  # nosec B608
        list_sql = (
            "SELECT id, type, path, title, track_id, referrer, visitor_id, visitor_hash, "  # nosec B608
            "session_id, country, region, city, occurred_at "
            "FROM events WHERE "
            + where
            + " ORDER BY "
            + sort_col
            + " "
            + order_sql
            + " LIMIT :limit OFFSET :offset"
        )
        # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
        count_row = conn.execute(text(count_sql), params).scalar_one()
        # nosemgrep: python.sqlalchemy.security.audit.avoid-sqlalchemy-text.avoid-sqlalchemy-text
        rows = conn.execute(text(list_sql), params).mappings()
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
            _COUNT_VISITORS_SQL,
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
            _VISITS_SERIES_HOURLY_SQL,
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
            _VISITS_SERIES_DAILY_SQL,
            {"site_id": site_id, "date_from": date_from, "date_to": date_to, "tz": tz},
        ).mappings()
        return [dict(r) for r in rows]
