"""A genui ThreadStore on Postgres (``pip install asyncpg``).

One row per message, ordered by an identity column. ``append`` inserts all of a turn's
messages in one statement, so a turn is stored whole or not at all.

    pool = await asyncpg.create_pool("postgresql://localhost/app")
    store = PostgresThreadStore(pool)
    await store.create_table()   # once, or put SCHEMA in your migrations
"""

from __future__ import annotations

import json
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS genui_messages (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    thread_key TEXT        NOT NULL,
    message    JSONB       NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS genui_messages_thread ON genui_messages (thread_key, id);
"""


class PostgresThreadStore:
    def __init__(self, pool: Any, *, max_messages: int = 500) -> None:
        self.pool = pool
        self.max_messages = max_messages

    async def create_table(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute(SCHEMA)

    async def load(self, key: str) -> list[dict[str, Any]]:
        rows = await self.pool.fetch(
            "SELECT message FROM (SELECT id, message FROM genui_messages WHERE thread_key = $1 "
            "ORDER BY id DESC LIMIT $2) newest ORDER BY id",
            key, self.max_messages,
        )
        return [json.loads(r["message"]) for r in rows]

    async def append(self, key: str, messages: list[dict[str, Any]]) -> None:
        if not messages:
            return
        await self.pool.execute(
            "INSERT INTO genui_messages (thread_key, message) "
            "SELECT $1, m FROM unnest($2::jsonb[]) WITH ORDINALITY AS t(m, n) ORDER BY n",
            key, [json.dumps(m, ensure_ascii=False) for m in messages],
        )

    async def delete(self, key: str) -> None:
        await self.pool.execute("DELETE FROM genui_messages WHERE thread_key = $1", key)
