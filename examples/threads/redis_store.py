"""A genui ThreadStore on Redis (``pip install redis``).

Each thread is a Redis list of JSON messages. Appends are one atomic RPUSH, threads expire
after ``ttl`` seconds of inactivity, and each list is trimmed to the newest ``max_messages``.

    from redis.asyncio import Redis
    store = RedisThreadStore(Redis.from_url("redis://localhost:6379/0"))
"""

from __future__ import annotations

import json
from typing import Any


class RedisThreadStore:
    def __init__(self, redis: Any, *, prefix: str = "genui:thread:", ttl: int | None = 60 * 60 * 24 * 30,
                 max_messages: int = 500) -> None:
        self.redis = redis
        self.prefix = prefix
        self.ttl = ttl
        self.max_messages = max_messages

    def _key(self, key: str) -> str:
        return self.prefix + key

    async def load(self, key: str) -> list[dict[str, Any]]:
        raw = await self.redis.lrange(self._key(key), 0, -1)
        return [json.loads(m) for m in raw]

    async def append(self, key: str, messages: list[dict[str, Any]]) -> None:
        if not messages:
            return
        k = self._key(key)
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.rpush(k, *(json.dumps(m, ensure_ascii=False) for m in messages))
            pipe.ltrim(k, -self.max_messages, -1)
            if self.ttl:
                pipe.expire(k, self.ttl)
            await pipe.execute()

    async def delete(self, key: str) -> None:
        await self.redis.delete(self._key(key))
