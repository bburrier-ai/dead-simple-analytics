from uuid import UUID

from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DbConn, DemoMode
from demo import fixtures as demo_fixtures
from services.events import EventsService

router = APIRouter(prefix="/events", tags=["events"])
service = EventsService()


@router.get("")
def list_events(
    user: CurrentUser,
    conn: DbConn,
    demo_mode: DemoMode,
    site_id: UUID = Query(...),
    type: str = Query("all"),
    q: str | None = Query(None),
    sort: str = Query("occurred_at"),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    _ = user
    if demo_mode:
        return demo_fixtures.list_events(
            site_id,
            event_type=type,
            q=q,
            sort=sort,
            order=order,
            page=page,
            limit=limit,
        )
    return service.list_events(
        conn,
        site_id,
        event_type=type,
        q=q,
        sort=sort,
        order=order,
        page=page,
        limit=limit,
    )
