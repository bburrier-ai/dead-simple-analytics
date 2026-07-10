"""In-process pub/sub for dashboard live updates (SSE).

Single-worker uvicorn is assumed; no Redis. Collect publishes a tiny
site_id notice; the dashboard refreshes via existing HTTP endpoints.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

logger = logging.getLogger(__name__)


class LiveHub:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def unbind_loop(self) -> None:
        self._loop = None
        self._subscribers.clear()

    @asynccontextmanager
    async def subscription(self) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=32)
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)

    def publish(self, event: dict[str, Any]) -> None:
        loop = self._loop
        if loop is None or not self._subscribers:
            return

        def _fanout() -> None:
            for queue in list(self._subscribers):
                try:
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    # Drop oldest, then retry once — prefer freshest signal.
                    try:
                        queue.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                    try:
                        queue.put_nowait(event)
                    except asyncio.QueueFull:
                        self._subscribers.discard(queue)

        try:
            loop.call_soon_threadsafe(_fanout)
        except RuntimeError:
            logger.debug("live hub publish skipped; event loop closed")

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


live_hub = LiveHub()
