import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.dependencies import CurrentUser
from core.live import live_hub

router = APIRouter(prefix="/events", tags=["events"])

KEEPALIVE_SEC = 25.0


@router.get("/live")
async def events_live(user: CurrentUser) -> StreamingResponse:
    _ = user

    async def event_stream() -> AsyncIterator[str]:
        async with live_hub.subscription() as queue:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=KEEPALIVE_SEC)
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                payload = json.dumps(event, separators=(",", ":"))
                yield f"event: event\ndata: {payload}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
