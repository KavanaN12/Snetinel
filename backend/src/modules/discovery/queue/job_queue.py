"""Redis-backed queue for discovery jobs."""

import json
from typing import Protocol

from redis.asyncio import Redis
from redis.exceptions import RedisError

from src.shared.config.settings import get_settings

settings = get_settings()


class JobQueue(Protocol):
    async def enqueue(self, job: dict[str, object]) -> None: ...

    async def dequeue(self) -> dict[str, object] | None: ...


class RedisJobQueue:
    def __init__(self, redis_url: str | None = None, queue_name: str | None = None) -> None:
        self._redis = Redis.from_url(redis_url or settings.REDIS_URL, decode_responses=True)
        self._queue_name = queue_name or settings.DISCOVERY_QUEUE_NAME
        self._fallback_jobs: list[dict[str, object]] = []

    async def enqueue(self, job: dict[str, object]) -> None:
        try:
            await self._redis.lpush(self._queue_name, json.dumps(job))
        except RedisError:
            self._fallback_jobs.append(job)

    async def dequeue(self) -> dict[str, object] | None:
        try:
            result = await self._redis.brpop(self._queue_name, timeout=5)
            if not result:
                return None
            _, payload = result
            return json.loads(payload)
        except RedisError:
            if not self._fallback_jobs:
                return None
            return self._fallback_jobs.pop(0)


class InMemoryJobQueue:
    def __init__(self) -> None:
        self._jobs: list[dict[str, object]] = []

    async def enqueue(self, job: dict[str, object]) -> None:
        self._jobs.append(job)

    async def dequeue(self) -> dict[str, object] | None:
        if not self._jobs:
            return None
        return self._jobs.pop(0)
