# Server-side history

The browser sends the whole conversation with every request, and a user can edit it. For agents that take actions (bookings, CRM writes, refunds), keep history on the server with `genui.threads`. Only the new user turn is read from the request.

| File | What it is |
| --- | --- |
| `app.py` | FastAPI app: `history()` + `autofix()` + `record()`. `THREADS=memory\|redis\|postgres`. |
| `redis_store.py` | `RedisThreadStore`: one list per thread, atomic appends, TTL, trimming. Needs `pip install redis`. |
| `postgres_store.py` | `PostgresThreadStore`: one row per message (JSONB), each turn inserted in one statement. Needs `pip install asyncpg`. ⚠️ Not yet tested against a live Postgres. |
| `test_stores.py` | Redis store tests against `fakeredis`. |

```bash
pip install "genui-py[fastapi,openai]" uvicorn redis
THREADS=redis REDIS_URL=redis://localhost:6379/0 GENUI_SPEC=spec.json uvicorn app:app --port 8000

# tests (no Redis server needed)
uv run --with fakeredis --with redis --with pytest --with pytest-asyncio pytest -q test_stores.py
```

**Key threads by user.** Thread ids come from the browser, so use `f"{user.id}:{run.thread_id}"`. Otherwise anyone who guesses an id can read someone else's thread. `app.py` takes the user id from an `X-User-Id` header as a placeholder; replace it with your real authentication.

Any object with async `load(key)`, `append(key, messages)` and `delete(key)` is a `ThreadStore`.
