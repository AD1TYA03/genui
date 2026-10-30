"""Wander backend: FastAPI + genui + Gemini.

Run:  uv run uvicorn app:app --reload --port 8000
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from genui.integrations.fastapi import read_run, stream_response

import agent

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Wander")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat")
async def chat(request: Request):
    run = await read_run(request)  # AG-UI RunAgentInput -> clean chat history (markers stripped, clicks formatted)
    return stream_response(agent.run_agent(run.messages), run=run)  # AG-UI SSE: text + TOOL_CALL_* events


@app.get("/api/health")
async def health():
    return {
        "ok": True,
        "model": agent.MODEL,
        "spec": agent.spec_path().name,
        "components": list(agent.library.components),
        "key": bool(agent.gemini_api_key()),
    }
