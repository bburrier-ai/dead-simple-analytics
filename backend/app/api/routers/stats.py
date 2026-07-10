from uuid import UUID

from fastapi import APIRouter, Query

from app.dependencies import CurrentUser, DbConn, DemoMode
from demo import fixtures as demo_fixtures
from services.stats import StatsService

router = APIRouter(prefix="/stats", tags=["stats"])
service = StatsService()


@router.get("/visits")
def visits(
    user: CurrentUser,
    conn: DbConn,
    demo_mode: DemoMode,
    site_id: UUID = Query(...),
    days: int = Query(14, ge=1, le=365),
    hours: int | None = Query(None, ge=1, le=168),
    tz: str | None = Query(None, max_length=64),
) -> dict:
    _ = user
    if demo_mode:
        if hours:
            return demo_fixtures.visits_stats(hours=hours, tz_name=tz)
        return demo_fixtures.visits_stats(days=days, tz_name=tz)
    if hours:
        return service.visits_hours(conn, site_id, hours=hours, tz_name=tz)
    return service.visits(conn, site_id, days=days, tz_name=tz)
