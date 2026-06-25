"""
AURA Backend main entrypoint.
Exposes WebSocket bridge and AI-powered chat endpoint.
"""

from __future__ import annotations

import os
import asyncio
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ame_backend.src.services.ai_engine import AIEngine
from ame_backend.src.automation.task_manager import TaskManager

app = FastAPI(title="AURA Backend")
ai = AIEngine()
task_mgr = TaskManager()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "ai": ai.health_check()}


@app.post("/api/chat")
def chat(payload: dict) -> dict:
    prompt = payload.get("prompt", "")
    context = payload.get("context")
    result = ai.chat(prompt=prompt, context=context)
    text = result.get("text", "")
    intent = result.get("intent")
    if intent and intent.get("action") == "START_BOT":
        target = intent.get("target", "surveys")
        if target == "surveys":
            payload.setdefault("start_url", "https://example.com/survey")
        status = task_mgr.start_survey_bot(payload.get("start_url", "https://example.com/survey"))
        return {
            "reply": text or "Bot de encuestas iniciado.",
            "intent": intent,
            "task_status": status,
        }
    return {"reply": text, "provider": result.get("provider")}


@app.websocket("/ws/bridge")
async def ws_bridge(ws: WebSocket) -> None:
    await ws.accept()
    queue: asyncio.Queue[str] = asyncio.Queue()
    shutdown = False

    async def reader() -> None:
        nonlocal shutdown
        while not shutdown:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue
            if msg.get("type") == "chat":
                prompt = msg.get("prompt", "")
                context = msg.get("context")
                result = ai.chat(prompt=prompt, context=context)
                text = result.get("text", "")
                intent = result.get("intent")
                if intent and intent.get("action") == "START_BOT":
                    status = task_mgr.start_survey_bot("https://example.com/survey")
                    await ws.send_text(
                        json.dumps(
                            {"type": "chat", "reply": text or "Iniciando bot...", "task": status}
                        )
                    )
                else:
                    await ws.send_text(
                        json.dumps(
                            {"type": "chat", "reply": text, "provider": result.get("provider")}
                        )
                    )
            elif msg.get("type") == "task_stop":
                task_mgr.stop_survey_bot()

    async def writer() -> None:
        nonlocal shutdown
        while not shutdown:
            item = await queue.get()
            await ws.send_text(item)

    reader_task = asyncio.create_task(reader())
    writer_task = asyncio.create_task(writer())

    def emit_log(payload: str) -> None:
        try:
            queue.put_nowait(payload)
        except Exception:
            pass

    loop = asyncio.get_event_loop()
    original_run_survey = getattr(task_mgr._solver, "solve_survey", None)

    async def patched_run_survey(start_url: str) -> None:
        setattr(task_mgr._solver, "_on_event", emit_log)
        if original_run_survey:
            await original_run_survey(start_url)

    setattr(task_mgr._solver, "solve_survey", patched_run_survey)

    try:
        while True:
            await asyncio.sleep(0.25)
    except WebSocketDisconnect:
        pass
    finally:
        shutdown = True
        reader_task.cancel()
        writer_task.cancel()
        try:
            await reader_task
        except Exception:
            pass
        try:
            await writer_task
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("ame_backend.src.main:app", host="0.0.0.0", port=8000, reload=False)
