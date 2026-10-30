from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from genui.integrations.fastapi import read_run, stream_response


def test_fastapi_endpoint_streams_agui():
    app = FastAPI()

    @app.post("/api/chat")
    async def chat(request: Request):
        run = await read_run(request)
        async def agent():
            yield f'root = Text("you said: {run.last_user_message}")'
        return stream_response(agent(), run=run)

    r = TestClient(app).post("/api/chat", json={"threadId": "t1", "runId": "r1",
                                                "messages": [{"id": "1", "role": "user", "content": "hi"}]})
    assert r.headers["content-type"].startswith("text/event-stream")
    assert '"threadId":"t1"' in r.text and "you said: hi" in r.text and "RUN_FINISHED" in r.text
