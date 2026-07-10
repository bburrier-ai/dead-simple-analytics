from uuid import UUID

from sqlalchemy.engine import Connection

from core.serialize import serialize_row
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
    ) -> dict:
        items, total = self.repo.list_events(
            conn,
            site_id,
            event_type=event_type,
            q=q,
            sort=sort,
            order=order,
            page=page,
            limit=limit,
        )
        return {
            "items": [serialize_row(i) for i in items],
            "total": total,
            "page": page,
            "limit": limit,
        }
