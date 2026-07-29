from uuid import UUID

from sqlalchemy.engine import Connection

from core.serialize import serialize_row
from core.time_window import period_bounds
from db.repositories.events import EventsRepository


class EventsService:
    def __init__(self) -> None:
        self.repo = EventsRepository()

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
        days: int | None = None,
        hours: int | None = None,
        tz_name: str | None = None,
    ) -> dict:
        bounds = period_bounds(days=days, hours=hours, tz_name=tz_name)
        start = bounds[0] if bounds else None
        end = bounds[1] if bounds else None
        items, total = self.repo.list_events(
            conn,
            site_id,
            event_type=event_type,
            q=q,
            sort=sort,
            order=order,
            page=page,
            limit=limit,
            start=start,
            end=end,
        )
        return {
            "items": [serialize_row(i) for i in items],
            "total": total,
            "page": page,
            "limit": limit,
        }
