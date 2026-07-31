from uuid import UUID

from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DemoMode, EventsSvc
from demo import fixtures as demo_fixtures

router = APIRouter(prefix="/events", tags=["events"])


@router.get("")
def list_events(
    user: CurrentUser,
    service: EventsSvc,
    demo_mode: DemoMode,
    site_id: UUID = Query(...),
    type: str = Query("all"),
    q: str | None = Query(None),
    sort: str = Query("occurred_at"),
    order: str = Query("desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    days: int | None = Query(None, ge=1, le=365),
    hours: int | None = Query(None, ge=1, le=168),
    tz: str | None = Query(None, max_length=64),
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
            days=days,
            hours=hours,
            tz_name=tz,
        )
    return service.list_events(
        site_id,
        event_type=type,
        q=q,
        sort=sort,
        order=order,
        page=page,
        limit=limit,
        days=days,
        hours=hours,
        tz_name=tz,
    )
