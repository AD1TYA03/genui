"""Server-side history with genui: the model only sees turns your server stored.

    pip install "genui-py[fastapi,openai]" uvicorn            # + redis or asyncpg for those stores
    THREADS=memory uvicorn app:app --port 8000                # or THREADS=redis / THREADS=postgres

The browser still sends its history (OpenUI's client always does); this app ignores all of it
except the new user turn. Replace `user_id` with your real authentication.
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, Request
from openai import AsyncOpenAI

from genui import Library, autofix
from genui.integrations.fastapi import read_run, stream_response
from genui.threads import MemoryThreadStore, ThreadStore, history, record

library = Library.from_spec(os.environ.get("GENUI_SPEC", "spec.json"))
SYSTEM = {"role": "system", "content": library.system_prompt()}
MODEL = os.environ.get("MODEL", "gpt-5.5-mini")
client = AsyncOpenAI()
store: ThreadStore = MemoryThreadStore()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global store
    kind = os.environ.get("THREADS", "memory")
    if kind == "redis":
        from redis.asyncio import Redis
        from redis_store import RedisThreadStore

        store = RedisThreadStore(Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0")))
    elif kind == "postgres":
        import asyncpg
        from postgres_store import PostgresThreadStore

        pg = PostgresThreadStore(await asyncpg.create_pool(os.environ["DATABASE_URL"]))
        await pg.create_table()
        store = pg
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/api/chat")
async def chat(request: Request, x_user_id: str = Header(...)):
    run = await read_run(request)
    key = f"{x_user_id}:{run.thread_id}"  # never key by thread id alone: ids come from the browser
    messages = await history(store, key, run)

    async def call_model(fix):
        return await client.chat.completions.create(model=MODEL, messages=[SYSTEM, *messages, *fix], stream=True)

    return stream_response(record(store, key, run, autofix(call_model, library)), run=run)
