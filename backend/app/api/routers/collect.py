import json

from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.api.schemas import CollectEvent
from app.dependencies import DbConn
from services.collect import CollectService

router = APIRouter(tags=["collect"])
service = CollectService()


@router.post("/collect")
async def collect(request: Request, conn: DbConn) -> dict:
    # Accept application/json and text/plain (sendBeacon-friendly; avoids CORS preflight).
    raw = await request.body()
    try:
        data = json.loads(raw.decode("utf-8") or "null")
        body = CollectEvent.model_validate(data)
    except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
        raise RequestValidationError(
            [
                {
                    "type": "value_error",
                    "loc": ["body"],
                    "msg": "Invalid collect payload",
                    "input": None,
                }
            ]
        ) from exc

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
