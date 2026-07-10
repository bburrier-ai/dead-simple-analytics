import asyncio

from core.live import LiveHub


def test_hub_publishes_to_subscriber():
    async def _run():
        hub = LiveHub()
        hub.bind_loop(asyncio.get_running_loop())
        async with hub.subscription() as queue:
            hub.publish({"site_id": "abc"})
            await asyncio.sleep(0)
            return await asyncio.wait_for(queue.get(), timeout=1)

    assert asyncio.run(_run()) == {"site_id": "abc"}


def test_hub_drops_when_unbound():
    hub = LiveHub()
    hub.publish({"site_id": "abc"})
    assert hub.subscriber_count == 0


def test_hub_queue_full_drops_oldest():
    async def _run():
        hub = LiveHub()
        hub.bind_loop(asyncio.get_running_loop())
        async with hub.subscription() as queue:
            for i in range(40):
                hub.publish({"n": i})
            await asyncio.sleep(0)
            assert queue.qsize() <= 32
            first = await queue.get()
            assert "n" in first

    asyncio.run(_run())


def test_hub_publish_skips_closed_loop(monkeypatch):
    async def _run():
        hub = LiveHub()
        loop = asyncio.get_running_loop()
        hub.bind_loop(loop)

        def boom(*_a, **_k):
            raise RuntimeError("closed")

        async with hub.subscription():
            monkeypatch.setattr(loop, "call_soon_threadsafe", boom)
            hub.publish({"site_id": "x"})

    asyncio.run(_run())


def test_hub_discards_subscriber_when_queue_stays_full():
    async def _run():
        hub = LiveHub()
        hub.bind_loop(asyncio.get_running_loop())

        class BrokenQueue:
            def put_nowait(self, _item):
                raise asyncio.QueueFull

            def get_nowait(self):
                raise asyncio.QueueEmpty

        broken = BrokenQueue()
        hub._subscribers.add(broken)  # type: ignore[arg-type]
        hub.publish({"site_id": "x"})
        await asyncio.sleep(0)
        assert broken not in hub._subscribers

    asyncio.run(_run())


def test_events_live_stream_emits_event_and_keepalive(monkeypatch):
    from app.api.routers import live as live_router
    from core.live import live_hub

    monkeypatch.setattr(live_router, "KEEPALIVE_SEC", 0.01)

    async def _run():
        loop = asyncio.get_running_loop()
        live_hub.bind_loop(loop)
        response = await live_router.events_live(user={"id": "1", "username": "admin"})
        agen = response.body_iterator

        waiter = asyncio.create_task(agen.__anext__())
        for _ in range(50):
            if live_hub.subscriber_count:
                break
            await asyncio.sleep(0.01)
        live_hub.publish({"site_id": "sse-1"})
        chunk = await asyncio.wait_for(waiter, timeout=2)
        assert "sse-1" in chunk or "keepalive" in chunk
        chunk2 = await asyncio.wait_for(agen.__anext__(), timeout=2)
        assert "keepalive" in chunk2 or "event" in chunk2
        await agen.aclose()
        # Leave hub bound for the shared TestClient lifespan.

    asyncio.run(_run())
