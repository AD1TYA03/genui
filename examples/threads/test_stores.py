"""Run: uv run --with fakeredis --with redis --with pytest --with pytest-asyncio pytest -q test_stores.py"""

import pytest

fakeredis = pytest.importorskip("fakeredis")

from redis_store import RedisThreadStore


@pytest.mark.asyncio
async def test_redis_store_round_trip_trim_and_ttl():
    redis = fakeredis.FakeAsyncRedis()
    store = RedisThreadStore(redis, ttl=60, max_messages=3)
    await store.append("u:t", [{"role": "user", "content": "ünïcode"}, {"role": "assistant", "content": "a"}])
    await store.append("u:t", [{"role": "user", "content": str(i)} for i in range(3)])
    assert [m["content"] for m in await store.load("u:t")] == ["0", "1", "2"]
    assert 0 < await redis.ttl("genui:thread:u:t") <= 60
    await store.append("u:t", [])
    await store.delete("u:t")
    assert await store.load("u:t") == []
