from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
import asyncio


@dataclass
class CacheEntry:
    value: Any
    expires_at: datetime


class MemoryCache:
    """Per-process cache; intentional: serverless hosts require an external cache for persistence."""

    def __init__(self, ttl_seconds: int):
        self.ttl = timedelta(seconds=ttl_seconds)
        self.entries: dict[str, CacheEntry] = {}
        self.inflight: dict[str, asyncio.Task[Any]] = {}

    async def get_or_set(self, key: str, factory: Callable[[], Awaitable[Any]]) -> Any:
        now = datetime.now(timezone.utc)
        entry = self.entries.get(key)
        if entry and entry.expires_at > now:
            return entry.value
        task = self.inflight.get(key)
        if task is None:
            task = asyncio.create_task(factory())
            self.inflight[key] = task
        try:
            value = await task
            self.entries[key] = CacheEntry(value=value, expires_at=datetime.now(timezone.utc) + self.ttl)
            return value
        finally:
            if task.done():
                self.inflight.pop(key, None)
