"""In-process pub/sub for live market data (WebSockets, DECISIONS.md #8).

v1 scale runs a single API process, so an in-process bus suffices; the
publish() seam is where Redis pub/sub slots in when the API scales out.
"""
from __future__ import annotations

import asyncio
from collections import defaultdict


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, world_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers[world_id].add(queue)
        return queue

    def unsubscribe(self, world_id: str, queue: asyncio.Queue) -> None:
        self._subscribers[world_id].discard(queue)

    def publish(self, world_id: str, message: dict) -> None:
        for queue in list(self._subscribers.get(world_id, ())):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                pass  # slow consumer loses ticks, not correctness


bus = EventBus()
