from fastapi import APIRouter, Request, Response

from app.api.schemas import CollectEvent
from app.dependencies import DbConn
from services.collect import CollectService

router = APIRouter(tags=["collect"])
service = CollectService()


@router.post("/collect")
def collect(body: CollectEvent, request: Request, conn: DbConn) -> dict:
    client_ip = request.client.host if request.client else None
    service.ingest(
        conn,
        body.model_dump(),
        client_ip=client_ip,
        user_agent=request.headers.get("user-agent"),
        origin=request.headers.get("origin"),
        referer=request.headers.get("referer"),
    )
    return {"ok": True}


@router.options("/collect")
def collect_options() -> Response:
    return Response(status_code=204)
