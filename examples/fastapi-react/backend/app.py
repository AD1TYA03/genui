"""genui demo backend: OpenUI's React chat UI, a Python agent, any model, no cloud in between.

Run:  OPENAI_API_KEY=... uv run uvicorn app:app --reload --port 8000
Local model instead (Ollama):  OPENAI_BASE_URL=http://localhost:11434/v1 OPENAI_API_KEY=ollama MODEL=qwen3 ...
"""
import os
from pathlib import Path

from fastapi import FastAPI, Request
from openai import AsyncOpenAI

from genui import Library
from genui.integrations.fastapi import read_run, stream_response

# spec.json is written by the frontend (`npm run generate`) from the same React component library,
# so the prompt and the renderer can never drift apart.
library = Library.from_spec(Path(__file__).with_name("spec.json"))
SYSTEM_PROMPT = library.system_prompt()

client = AsyncOpenAI()  # reads OPENAI_API_KEY / OPENAI_BASE_URL
MODEL = os.environ.get("MODEL", "gpt-5.5-mini")

app = FastAPI()


@app.post("/api/chat")
async def chat(request: Request):
    run = await read_run(request)  # history from the UI, markers stripped, button clicks formatted
    stream = await client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, *run.messages],
        stream=True,
    )
    return stream_response(stream, run=run)  # AG-UI events the React renderer understands
