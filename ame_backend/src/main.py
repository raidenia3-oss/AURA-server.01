"""
AURA Backend main entrypoint.
Exposes WebSocket bridge, AI-powered chat endpoint, telemetry and resilience features.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import FileResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


from ame_backend.src.automation.self_healing import SelfHealingDaemon
from ame_backend.src.automation.task_manager import TaskManager
from ame_backend.src.database.database import Database
from ame_backend.src.services.ai_engine import AIEngine
from ame_backend.src.api.api_service import app as telemetry_app
from ame_backend.src import models as db_models
from ame_backend.src.neural_core import EvolutionCore
from ame_backend.src.neural_core import SemanticMemory
from ame_backend.src import keep_alive as keep_alive_mod
from ame_backend.src.tools import browser

logger = logging.getLogger(__name__)

app = FastAPI(title="AURA Backend")
ai = AIEngine()
task_mgr = TaskManager()
db = Database()

# Núcleo Evolutivo: memoria (SQLAlchemy) + neurona + sys vitals + keep-alive.
db_models.init_db()
core = EvolutionCore(keep_alive_fn=keep_alive_mod.trigger_keep_alive)
memory = SemanticMemory()

healer = SelfHealingDaemon(task_manager=task_mgr)

# Métricas de Sys Vitals (entradas de la neurona). psutil si está disponible,
# sino métricas estándar de tiempo de respuesta y contador de mensajes.
try:
    import psutil

    _HAS_PSUTIL = True
except Exception:  # pragma: no cover
    psutil = None  # type: ignore
    _HAS_PSUTIL = False

_msg_counter = {"count": 0, "window": 0.0}


def collect_sys_vitals() -> dict:
    """Recolecta métricas reales del servidor para alimentar la neurona."""
    vitals: dict = {
        "latency_ms": 0.0,
        "memory_percent": 0.0,
        "cpu_percent": 0.0,
        "health_pings": 1.0,
        "msg_rate": 0.0,
    }
    if _HAS_PSUTIL:
        try:
            vitals["memory_percent"] = round(psutil.virtual_memory().percent, 2)
            vitals["cpu_percent"] = round(psutil.cpu_percent(interval=None), 2)
        except Exception:
            pass
    # Tasa de mensajes por segundo (ventana simple).
    _msg_counter["count"] += 0
    vitals["msg_rate"] = min(1.0, _msg_counter["count"] / 100.0)
    return vitals

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers must be included BEFORE mounting the telemetry app at "/", otherwise
# the root mount shadows every subsequent path (they would 404).

# Browser-control skill (optional; safe to skip if the module fails to load)
try:
    from ame_backend.src.api.skills_browser_control import router as browser_control_router

    app.include_router(browser_control_router)
except Exception as _exc:  # pragma: no cover - optional dependency
    logger.warning("No se pudo montar el router browser-control: %s", _exc)

# Admin: multi-server management (optional)
try:
    from ame_backend.src.api.admin_servers import router as admin_servers_router

    app.include_router(admin_servers_router)
except Exception as _exc:  # pragma: no cover - optional
    logger.warning("No se pudo montar el router admin-servers: %s", _exc)

# Serve the local dashboard HTML from the repo root, BEFORE mounting the
# telemetry app at "/" so this route is never shadowed (404 bug fix).
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    dashboard_path = Path(__file__).resolve().parents[2] / "dashboard_local.html"
    try:
        return dashboard_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return (
            "<html><body style='font-family:sans-serif'>"
            "<h1>AURA Dashboard</h1>"
            "<p>No se encontro dashboard_local.html en la raiz del proyecto.</p>"
            "</body></html>"
        )


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "ai": ai.health_check()}


@app.post("/api/chat")
def chat(payload: dict) -> dict:
    prompt = payload.get("prompt", "")
    context = payload.get("context")

    # 1) NAVEGACIÓN WEB AUTÓNOMA ("garras en la red").
    #    - Si el usuario incluye un enlace -> rasparlo y usarlo como contexto.
    #    - Si pide "busca en internet: <tema>" -> GOOGLEar y raspar resultados.
    web_context = ""
    urls = browser.find_urls(prompt)
    web_trigger = False
    m = __import__("re").search(r"busca\s+en\s+internet\s*:\s*(.+)", prompt, __import__("re").IGNORECASE)
    if m:
        web_trigger = True
        topic = m.group(1).strip()
        try:
            from ame_backend.src.tools import web_search

            found = web_search.search(topic, num_results=3)
            for fu in found:
                urls.append(fu)
        except Exception as exc:
            logger.error("Búsqueda web falló: %s", exc)
    for u in list(dict.fromkeys(urls))[:3]:  # úncias, máx 3
        try:
            snippet = browser.fetch_clean_text(u, timeout=15.0, max_chars=4000)
            if snippet:
                web_context += f"\n\n[Fuente: {u}]\n{snippet}\n"
        except Exception as exc:
            logger.error("No se pudo raspar %s: %s", u, exc)

    # 2) MEMORIA SEMÁNTICA (RAG): recordar sinápsis del usuario.
    try:
        if prompt.strip():
            memory.remember(prompt, kind="chat")
    except Exception as exc:
        logger.error("No se guardó memoria semántica: %s", exc)

    # Construir contexto enriquecido: RAG + web.
    rag_context = ""
    try:
        rag_context = memory.build_context(prompt or web_context, top_k=3)
    except Exception as exc:
        logger.error("RAG falló: %s", exc)

    enriched_context = context or ""
    if rag_context:
        enriched_context += f"\n\n{rag_context}"
    if web_context:
        enriched_context += f"\n\n[Contexto de internet en vivo]:{web_context}"
    if web_trigger:
        enriched_context += (
            "\n\n(INSTRUCCIÓN: responde usando SOLO el contexto de "
            "internet proporcionado arriba. Cita las fuentes.)"
        )

    # Memoria de estado: guardar el mensaje real del usuario.
    try:
        db_models.save_message(
            role="user", content=prompt, session_id="ws", context=enriched_context
        )
    except Exception as exc:
        logger.error("No se pudo guardar mensaje de usuario: %s", exc)

    result = ai.chat(prompt=prompt, context=enriched_context or None)
    text = result.get("text", "")
    provider = result.get("provider")
    intent = result.get("intent")

    # Memoria de estado: guardar la respuesta real del asistente.
    try:
        db_models.save_message(
            role="assistant", content=text, provider=provider, session_id="ws"
        )
    except Exception as exc:
        logger.error("No se pudo guardar respuesta: %s", exc)

    if intent and intent.get("action") == "START_BOT":
        start_url = payload.get("start_url", "https://example.com/survey")
        status = task_mgr.start_survey_bot(start_url)
        healer.record_activity("surveys", url=start_url)
        return {
            "reply": text or "Bot de encuestas iniciado.",
            "intent": intent,
            "task_status": status,
        }
    return {"reply": text, "provider": provider}


@app.get("/api/chat/history")
def chat_history(limit: int = 50) -> dict:
    """Historial real de mensajes (chat_history)."""
    try:
        return {"messages": db_models.recent_messages(limit=limit), "total": db_models.count_messages()}
    except Exception as exc:
        logger.error("No se pudo leer el historial: %s", exc)
        return {"messages": [], "total": 0, "error": str(exc)}


@app.get("/api/memory")
def memory_endpoint(limit: int = 20) -> dict:
    """Memoria semántica (RAG) persistida."""
    try:
        return {"memories": db_models.recent_memories(limit=limit), "total": db_models.count_memories()}
    except Exception as exc:
        logger.error("No se pudo leer memoria: %s", exc)
        return {"memories": [], "total": 0, "error": str(exc)}


# ------------------------------------------------------------------ #
# Módulo de Visión (multimodal nativo con Gemini 2.0 Flash)
# ------------------------------------------------------------------ #
_ALLOWED_IMAGE_TYPES = {
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/webp": "webp",
}


@app.post("/api/vision")
async def vision(file: UploadFile = File(...), prompt: str = "Describe esta imagen en detalle."):
    """Recibe una imagen y la analiza con visión multimodal de Gemini.

    El análisis generado se indexa en ``semantic_memory`` con
    ``kind='[VISION]'`` para que AURA recuerde visualmente lo procesado.
    """
    content_type = (file.content_type or "").lower()
    if content_type not in _ALLOWED_IMAGE_TYPES:
        return {
            "error": "tipo_no_soportado",
            "detail": f"Usa png, jpeg o webp (recibido: {content_type or 'desconocido'})",
        }

    raw = await file.read()
    if not raw:
        return {"error": "imagen_vacia", "detail": "No se recibieron bytes."}

    try:
        result = ai.vision(prompt=prompt, image_bytes=raw, mime_type=content_type)
    except Exception as exc:
        logger.error("Fallo de vision: %s", exc)
        return {"error": "vision_error", "detail": str(exc)}

    text = result.get("text", "")
    provider = result.get("provider")

    # Memoria de estado: guardar el analisis visual en el subconsciente.
    try:
        db_models.save_message(
            role="user",
            content=f"[VISION] {prompt}",
            provider=provider,
            session_id="vision",
        )
        db_models.save_message(
            role="assistant",
            content=text,
            provider=provider,
            session_id="vision",
        )
        # Indexar en memoria semántica (RAG) para recordar visualmente.
        memory.remember(f"[VISION] {prompt}\n{text}", kind="[VISION]")
    except Exception as exc:
        logger.error("No se pudo guardar vision en memoria: %s", exc)

    return {"analysis": text, "provider": provider}


@app.get("/neural/status")
def neural_status() -> dict:
    """Estado del Núcleo Evolutivo (neurona + Sys Vitals en vivo)."""
    vitals = collect_sys_vitals()
    try:
        tick = core.tick(vitals, alive=True)
    except Exception as exc:
        logger.error("Fallo del tick evolutivo: %s", exc)
        tick = {"error": str(exc)}
    return {
        "neural": core.status(),
        "last_tick": tick,
        "sys_vitals": vitals,
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "ai": ai.health_check()}


@app.websocket("/ws/bridge")
async def ws_bridge(ws: WebSocket) -> None:
    await ws.accept()
    queue: asyncio.Queue[str] = asyncio.Queue()
    shutdown = False

    # Latencia medida en tiempo real (entrada de la neurona).
    _latency_window: list[float] = []

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
                _msg_counter["count"] += 1
                # Memoria de estado: mensaje real del usuario.
                try:
                    db_models.save_message(role="user", content=prompt, session_id="ws")
                except Exception as exc:
                    logger.error("WS: no se guardó usuario: %s", exc)
                start = asyncio.get_event_loop().time()
                result = ai.chat(prompt=prompt, context=context)
                elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000
                _latency_window.append(elapsed_ms)
                if len(_latency_window) > 10:
                    _latency_window.pop(0)
                text = result.get("text", "")
                provider = result.get("provider")
                intent = result.get("intent")
                # Memoria de estado: respuesta real del asistente.
                try:
                    db_models.save_message(
                        role="assistant", content=text, provider=provider, session_id="ws"
                    )
                except Exception as exc:
                    logger.error("WS: no se guardó respuesta: %s", exc)
                if intent and intent.get("action") == "START_BOT":
                    start_url = "https://example.com/survey"
                    status = task_mgr.start_survey_bot(start_url)
                    healer.record_activity("surveys", url=start_url)
                    await ws.send_text(
                        json.dumps(
                            {"type": "chat", "reply": text or "Iniciando bot...", "task": status}
                        )
                    )
                else:
                    await ws.send_text(
                        json.dumps(
                            {"type": "chat", "reply": text, "provider": provider}
                        )
                    )
            elif msg.get("type") == "task_stop":
                task_mgr.stop_survey_bot()

    async def vitals_loop() -> None:
        nonlocal shutdown
        # Emite Sys Vitals reales + estado del Núcleo Evolutivo cada 2 s.
        while not shutdown:
            vitals = collect_sys_vitals()
            if _latency_window:
                vitals["latency_ms"] = round(sum(_latency_window) / len(_latency_window), 2)
            try:
                tick = core.tick(vitals, alive=True)
            except Exception as exc:
                logger.error("WS vitals tick falló: %s", exc)
                tick = {"error": str(exc)}
            payload = {
                "type": "vitals",
                "sys": vitals,
                "neural": core.status(),
                "tick": tick,
            }
            await ws.send_text(json.dumps(payload))
            await asyncio.sleep(2.0)

    async def writer() -> None:
        nonlocal shutdown
        while not shutdown:
            item = await queue.get()
            await ws.send_text(item)

    reader_task = asyncio.create_task(reader())
    writer_task = asyncio.create_task(writer())
    vitals_task = asyncio.create_task(vitals_loop())

    async def emit_log(payload: str) -> None:
        try:
            queue.put_nowait(payload)
        except Exception:
            pass

    loop = asyncio.get_running_loop()
    original_run_survey = getattr(task_mgr._solver, "solve_survey", None)

    async def patched_run_survey(start_url: str) -> None:
        setattr(task_mgr._solver, "_on_event", emit_log)
        healer.record_activity("surveys", url=start_url)
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
        vitals_task.cancel()
        try:
            await reader_task
        except Exception:
            pass
        try:
            await writer_task
        except Exception:
            pass
        try:
            await vitals_task
        except Exception:
            pass


@app.post("/emergency")
def emergency() -> dict:
    return {"status": "shutdown_initiated"}


# ------------------------------------------------------------------ #
# Servir el frontend (AURA UI / AmeAura, build de Vite) desde el mismo
# origen que la API, para que todo el sistema AURA cargue en la URL raiz de
# Render. Se registra DESPUES de todas las rutas /api/*, /health, /dashboard
# para que estas ganen y el static solo capture lo no-IAPI (/, /assets).
_STATIC_DIR = Path(__file__).resolve().parents[0] / "frontend_static"

# Assets compilados (JS/CSS) en /assets.
if (_STATIC_DIR / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=str(_STATIC_DIR / "assets")), name="frontend_assets")

# HTML de la SPA (index.html) en la raiz "/".
if _STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="frontend_spa")

# El telemetry_app expone /api/health, /api/status, etc. Se monta en
# /api para no sombrear el SPA y coincidir con lo que llama el frontend.
app.mount("/api", telemetry_app)


# ------------------------------------------------------------------ #
# Ciclo de vida / resiliencia
# ------------------------------------------------------------------ #

@app.on_event("startup")
async def on_startup() -> None:
    logger.info("AURA Backend starting up")
    await healer.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("AURA Backend shutting down")
    await healer.stop()
    try:
        now_iso = datetime.now().isoformat()
        saved = db.read("data/db.json", default={})
        saved["bots"] = [
            {"id": "bot-1", "name": "Roller Miner", "status": "Idle"},
            {"id": "bot-2", "name": "Survey Harvester", "status": "Stopped"},
            {"id": "bot-3", "name": "OSINT Recon", "status": "Stopped"},
        ]
        saved.setdefault("logs", []).append(
            {"ts": now_iso, "level": "INFO", "message": "Servidor apagado correctamente (graceful shutdown)"}
        )
        db.write("data/db.json", saved)
    except Exception as exc:
        logger.error("Error guardando estado final: %s", exc)

    try:
        task_mgr.stop_survey_bot()
    except Exception as exc:
        logger.error("Error deteniendo tareas al apagar: %s", exc)


def _handle_exit(signum: int, frame: Any) -> None:
    logger.info("Señal de terminación recibida (%s)", signum)
    sys.stderr.write(f"Recibida señal {signum}. Apagando gracefully...\n")
    try:
        task_mgr.stop_survey_bot()
    except Exception as exc:
        logger.error("Error en handler de señal: %s", exc)


for _sig in (signal.SIGTERM, signal.SIGINT):
    try:
        signal.signal(_sig, _handle_exit)
    except Exception as exc:
        logger.debug("No se pudo registrar handler para %s: %s", _sig, exc)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("ame_backend.src.main:app", host="0.0.0.0", port=8000, reload=False)
