from uuid import UUID

from sqlalchemy.engine import Engine

from core.serialize import serialize_row
from core.time_window import period_bounds
from db.repositories.events import EventsRepository


class EventsService:
    def __init__(self, engine: Engine | None = None) -> None:
        self._engine = engine
        self.repo = EventsRepository()

    def list_events(
        self,
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
        with self._require_engine().begin() as conn:
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

    def _require_engine(self) -> Engine:
        if self._engine is None:
            raise RuntimeError("EventsService requires a database engine")
        return self._engine
