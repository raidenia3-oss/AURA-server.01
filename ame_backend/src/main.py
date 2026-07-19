"""
AURA Backend main entrypoint.
Exposes WebSocket bridge, AI-powered chat endpoint, telemetry and resilience features.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
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
from ame_backend.src.tools import workspace as workspace_tools
from ame_backend.src.tools.multi_model_router import MultiModelRouter
from ame_backend.src.tools import orchestrator as orchestrator_mod
from ame_backend.src import neural_telemetry
from ame_backend.src.tools import discord_bot as discord_bridge_mod
from ame_backend.src.tools import rocket_bridge as rocket_bridge_mod
from ame_backend.src.tools import knowledge_ingest as knowledge_ingest_mod
from ame_backend.src.tools import cron_scheduler as cron_mod
from ame_backend.src.tools import agents_pool as agents_pool_mod

logger = logging.getLogger(__name__)

app = FastAPI(title="AURA Backend")
ai = AIEngine()
router_engine = MultiModelRouter(ai)
task_mgr = TaskManager()
db = Database()

# Red de Comunicación Soberana: clientes WebSocket de la Mesh privada.
mesh_clients: set = set()

# Puente Táctico de Discord (no bloquea el arranque si falta token/librería).
discord_bridge = discord_bridge_mod.DiscordBridge(ai, router_engine)

# Interfaz Soberana Definitiva: Puente de Rocket.Chat (REST/Webhooks).
# No-op si no están configuradas ROCKET_CHAT_URL + credenciales/webhook.
rocket_bridge = rocket_bridge_mod.RocketChatBridge(ai, router_engine)

# Autonomia Total: Cron proactivo y Pool multi-agente (Cismas de Conciencia).
cron_scheduler = cron_mod.CronScheduler(
    ai, discord_bridge,
    broadcast_fn=lambda payload: asyncio.ensure_future(broadcast_mesh(payload)),
    stability_provider=lambda: (core.last_stability or 1.0),
    rocket_bridge=rocket_bridge,
)
agents_pool = agents_pool_mod.AgentsPool(ai, router_engine)

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
        # Consulta técnica -> priorizar memoria [KNOWLEDGE].
        _technical = bool(
            re.search(
                r"\b(api|fastapi|react|endpoint|router|function|class|code|"
                r"documentacion|docstring|decorator|http|request|response|"
                r"embedding|modelo|llm|python|typescript|sql)\b",
                prompt or "",
                re.IGNORECASE,
            )
        )
        hits = memory.recall(prompt or web_context, top_k=3, technical=_technical)
        neural_telemetry.record_rag(prompt, len(hits))
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

    # Modo Libre: si el usuario lo activa, enrutar por el multi-model router
    # hacia modelos sin restricciones (OpenRouter/DeepInfra) con API key secundaria.
    if payload.get("free_mode"):
        try:
            free_res = router_engine.chat(
                prompt=prompt,
                context=enriched_context or None,
                free_mode=True,
                prefer=payload.get("free_prefer"),
            )
            neural_telemetry.record_router(call=True, error=False)
            if free_res.get("text"):
                text = free_res["text"]
                provider = free_res.get("provider", provider)
            else:
                neural_telemetry.record_router(call=True, error=True)
        except Exception as exc:
            logger.error("Modo Libre falló: %s", exc)
            neural_telemetry.record_router(call=True, error=True)

    # Módulo Operador de Workspace: si el usuario pide operar archivos locales,
    # Gemini decide (tool calling nativo) cuándo leer/escribir en el sandbox.
    _workspace_trigger = bool(
        re.search(
            r"(lee|analiza|revisa|muestra|escribe|crea|modifica|cambia|guarda|"
            r"edita|genera|lista|explora)\s+(el\s+)?(archivo|script|c[oó]digo|"
            r"fichero|carpeta|directorio|workspace)",
            prompt,
            re.IGNORECASE,
        )
    )
    if _workspace_trigger:
        try:
            ws_result = ai.chat_with_tools(prompt=prompt, context=enriched_context or None)
            ws_text = ws_result.get("text", "")
            if ws_text:
                text = ws_text
                provider = ws_result.get("provider", provider)
            calls = ws_result.get("tool_calls") or []
            for call in calls:
                res = call.get("result", {})
                if res.get("ok") and call.get("tool") == "write_workspace_file":
                    try:
                        memory.remember(
                            f"[WORKSPACE] {call.get('args', {}).get('path')} modificado "
                            f"por AURA.",
                            kind="[WORKSPACE]",
                        )
                    except Exception as exc:
                        logger.error("WS mem: %s", exc)
        except Exception as exc:
            logger.error("Tool calling falló, usando chat normal: %s", exc)

    # Cismas de Conciencia: si la tarea es [COMPLEJA], AURA ramifica en
    # sub-agentes (Architect + Shadow) que debaten 2 rondas y devuelven la
    # solucion ya filtrada y auditada (se ejecuta en hilo aparte, sin bloquear
    # el event loop de FastAPI).
    if agents_pool_mod.is_complex(prompt) and not payload.get("free_mode"):
        try:
            debate = agents_pool.debate_sync(prompt)
            if debate.get("ok") and debate.get("solution"):
                text = debate["solution"]
                provider = "multi-agent"
                try:
                    memory.remember(
                        f"[COMPLEJA] Debate multi-agente resuelto: {prompt[:200]}",
                        kind="[COMPLEJA]",
                    )
                except Exception as exc:
                    logger.error("Debate mem: %s", exc)
        except Exception as exc:
            logger.error("Debate multi-agente fallo, usando chat normal: %s", exc)

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


# ------------------------------------------------------------------ #
# Módulo Operador de Workspace ("manos" locales de AURA)
# ------------------------------------------------------------------ #
_WORKSPACE_TOOLS = {
    "read": workspace_tools.read_workspace_file,
    "list": workspace_tools.list_workspace_contents,
    "write": workspace_tools.write_workspace_file,
}


@app.post("/api/workspace")
def workspace_endpoint(payload: dict) -> dict:
    """Opera archivos dentro del sandbox local de AURA (Workspace Operator).

    Acciones:
      - ``list``:  {action:"list", path?:"", depth?:1}
      - ``read``:  {action:"read", path:"AME/recon.py"}
      - ``write``: {action:"write", path:"AME/notas.md", content:"...", append?:false}

    Las escrituras/modificaciones importantes generan un resumen automático
    indexado en ``semantic_memory`` con ``kind='[WORKSPACE]'``.
    """
    action = (payload or {}).get("action", "list")
    handler = _WORKSPACE_TOOLS.get(action)
    if handler is None:
        return {"ok": False, "error": "accion_no_soportada", "action": action}

    # Telemetría de la neurona: cada operación cuenta como actividad de AURA.
    neural_telemetry.record_workspace(op=True, blocked=False)

    try:
        if action == "list":
            result = handler(payload.get("path", ""), payload.get("depth", 1))
        elif action == "read":
            result = handler(payload.get("path", ""))
        else:  # write
            result = handler(
                payload.get("path", ""),
                payload.get("content", ""),
                bool(payload.get("append", False)),
            )
        # Un bloqueo de sandbox (path traversal / no autorizado) es señal de
        # seguridad para la neurona.
        if isinstance(result, dict) and not result.get("ok") and result.get("error") in (
            "Acceso denegado",
            "archivo_no_autorizado",
        ):
            neural_telemetry.record_workspace(op=False, blocked=True)
    except Exception as exc:
        logger.error("Fallo de workspace (%s): %s", action, exc)
        neural_telemetry.record_workspace(op=False, blocked=True)
        return {"ok": False, "error": "workspace_error", "detail": str(exc)}

    # Persistencia semántica de modificaciones importantes.
    if action == "write" and result.get("ok"):
        path = result.get("path", "")
        content = payload.get("content", "")
        try:
            summary = (
                f"[WORKSPACE] Modificación de archivo: {path} "
                f"({result.get('bytes_written', 0)} bytes, modo {result.get('mode')}). "
                f"Resumen: {content[:400]}"
            )
            memory.remember(summary, kind="[WORKSPACE]")
            db_models.save_message(
                role="user",
                content=f"[WORKSPACE] write {path}",
                provider="workspace",
                session_id="workspace",
            )
            db_models.save_message(
                role="assistant",
                content=summary,
                provider="workspace",
                session_id="workspace",
            )
        except Exception as exc:
            logger.error("No se guardó resumen [WORKSPACE]: %s", exc)

    # Lectura también se registra como recuerdo liviano para RAG futuro.
    if action == "read" and result.get("ok"):
        try:
            memory.remember(
                f"[WORKSPACE] Lectura de {result.get('path')}: "
                f"{result.get('content', '')[:600]}",
                kind="[WORKSPACE]",
            )
        except Exception as exc:
            logger.error("No se guardó lectura [WORKSPACE]: %s", exc)

    return result


# ------------------------------------------------------------------ #
# Enrutador Multi-Modelo ("Modo Libre") + Orquestador Autónomo
# ------------------------------------------------------------------ #
@app.post("/api/router")
def router_endpoint(payload: dict) -> dict:
    """Enrutador multi-modelo. Activa el "Modo Libre" con modelos sin censura.

    {action:"chat", prompt, free_mode?:bool, prefer?:"openrouter"|"deepinfra"}
    {action:"status"}  -> proveedores y disponibilidad de Modo Libre
    """
    action = (payload or {}).get("action", "status")
    if action == "status":
        return {
            "free_mode_available": router_engine.free_mode_available(),
            "providers": router_engine.list_providers(),
        }
    if action == "chat":
        prompt = payload.get("prompt", "")
        if not prompt:
            return {"ok": False, "error": "prompt_vacio"}
        free_mode = bool(payload.get("free_mode", False))
        prefer = payload.get("prefer")
        neural_telemetry.record_router(call=True, error=False)
        res = router_engine.chat(prompt=prompt, free_mode=free_mode, prefer=prefer)
        if not res.get("text") or res.get("error"):
            neural_telemetry.record_router(call=True, error=True)
        return res
    return {"ok": False, "error": "accion_no_soportada", "action": action}


@app.post("/api/orchestrator")
def orchestrator_endpoint(payload: dict) -> dict:
    """Orquestador Autónomo del Enjambre.

    Acciones:
      - analyze:  analiza rendimiento de la neurona y sugiere optimizaciones
      - scout:    recopila plataformas cloud alternativas (Server Scout)
      - deploy:   genera Dockerfile + docker-compose para un nuevo nodo
      - apply:    aplica una optimización propuesta (requiere aprobación)
    """
    action = (payload or {}).get("action", "analyze")
    try:
        if action == "analyze":
            neural_status = None
            try:
                neural_status = core.status()
            except Exception:
                pass
            return orchestrator_mod.analyze_performance(ai, neural_status)
        if action == "scout":
            return orchestrator_mod.scout_infrastructure()
        if action == "deploy":
            return orchestrator_mod.generate_deployment_config(
                target=payload.get("target", "generic"),
                port=int(payload.get("port", 8000)),
            )
        if action == "apply":
            return orchestrator_mod.apply_optimization(
                payload.get("path", ""),
                payload.get("original", ""),
                payload.get("optimized", ""),
            )
        return {"ok": False, "error": "accion_no_soportada", "action": action}
    except Exception as exc:
        logger.error("Fallo de orchestrator (%s): %s", action, exc)
        return {"ok": False, "error": "orchestrator_error", "detail": str(exc)}


# ------------------------------------------------------------------ #
# Replicación y Redundancia Multi-Nodo (Supervivencia 100% Uptime)
# ------------------------------------------------------------------ #
_SWARM_TOKEN = os.getenv("SWARM_TOKEN", "aura-swarm-secret")


def _swarm_auth(provided: Optional[str]) -> bool:
    if not _SWARM_TOKEN:
        return False
    return provided == _SWARM_TOKEN


@app.post("/api/enjambre/sincronizar")
def enjambre_sincronizar(payload: dict) -> dict:
    """Nodo secundario (Koyeb/Fly) solicita una copia ligera del estado.

    Protegido por ``SWARM_TOKEN`` (header ``X-Swarm-Token`` o campo ``token``).
    Devuelve historial de chat, memorias semánticas y pesos de la neurona.
    """
    provided = (payload or {}).get("token") or (payload or {}).get("X-Swarm-Token")
    if not _swarm_auth(provided):
        return {"ok": False, "error": "unauthorized"}
    try:
        chat_limit = int((payload or {}).get("chat_limit", 20))
        memory_limit = int((payload or {}).get("memory_limit", 50))
    except Exception:
        chat_limit, memory_limit = 20, 50
    return orchestrator_mod.package_swarm_state(
        chat_limit=chat_limit, memory_limit=memory_limit
    )


@app.post("/api/knowledge/ingest")
def knowledge_ingest_endpoint(payload: dict) -> dict:
    """Ingesta conocimiento senior (texto/código/URL) al cerebro RAG.

    Acepta {text|code|url, source?}. Divide en chunks, genera embeddings
    con GeminiEmbedder y los guarda en semantic_memory con tag [KNOWLEDGE].
    """
    try:
        return knowledge_ingest_mod.ingest(payload or {})
    except Exception as exc:
        logger.error("Fallo de knowledge ingest: %s", exc)
        return {"ok": False, "error": "knowledge_ingest_error", "detail": str(exc)}


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
# Red de Comunicación Soberana — AmeAura Private Mesh
# ------------------------------------------------------------------ #
_MESH_KEY = os.getenv("MESH_KEY", "aura-mesh-secret")


def _mesh_key_valid(provided: Optional[str]) -> bool:
    if not _MESH_KEY:
        return False
    return provided == _MESH_KEY


@app.get("/mesh")
def mesh_mobile_page() -> HTMLResponse:
    """Sirve la interfaz móvil ultra-ligera de la Red Privada (ciberpunk)."""
    html_path = _STATIC_DIR / "mesh_mobile.html"
    try:
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return HTMLResponse(
            "<html><body style='font-family:sans-serif'>"
            "<h1>AmeAura Private Mesh</h1><p>mesh_mobile.html no encontrado.</p>"
            "</body></html>"
        )


@app.websocket("/api/mesh/stream")
async def mesh_stream(ws: WebSocket) -> None:
    """WebSocket privado de la Mesh, protegido por header X-Mesh-Key.

    El cliente envía JSON: {"prompt": "...", "free_mode": bool}.
    El servidor responde con el texto de AURA (chat_with_tools o Modo Libre)
    y puede difundir alertas de la Neurona a todos los nodos conectados.
    """
    provided = ws.headers.get("X-Mesh-Key") or ws.query_params.get("key")
    if not _mesh_key_valid(provided):
        await ws.accept()
        await ws.send_text(json.dumps({"type": "error", "detail": "unauthorized"}))
        await ws.close()
        return
    await ws.accept()
    mesh_clients.add(ws)
    try:
        await ws.send_text(
            json.dumps({"type": "ready", "provider": "AmeAura Private Mesh"})
        )
        while True:
            data = await ws.receive_text()
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue
            prompt = (msg.get("prompt") or "").strip()
            if not prompt:
                continue
            free_mode = bool(msg.get("free_mode", False))
            try:
                if free_mode:
                    res = router_engine.chat(prompt=prompt, free_mode=True)
                    text = res.get("text") or res.get("error") or "(sin respuesta)"
                    tag = "🔓 [Libre]"
                else:
                    res = ai.chat_with_tools(prompt=prompt)
                    text = res.get("text") or "(sin respuesta)"
                    tag = "🧠 [AURA]"
                await ws.send_text(
                    json.dumps({"type": "reply", "tag": tag, "text": text})
                )
            except Exception as exc:
                logger.error("Mesh chat falló: %s", exc)
                await ws.send_text(
                    json.dumps({"type": "error", "detail": str(exc)})
                )
    except WebSocketDisconnect:
        pass
    finally:
        mesh_clients.discard(ws)


async def broadcast_mesh(payload: dict) -> None:
    """Difunde un payload JSON a todos los nodos conectados de la Mesh."""
    if not mesh_clients:
        return
    raw = json.dumps(payload)
    dead = set()
    for client in list(mesh_clients):
        try:
            await client.send_text(raw)
        except Exception:
            dead.add(client)
    mesh_clients.difference_update(dead)


async def broadcast_mesh_alert(message: str) -> None:
    """Difunde una alerta de la Neurona a todos los nodos de la Mesh."""
    await broadcast_mesh({"type": "alert", "text": message})


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

# Monitor de la Neurona: corre en su propio background task, ajeno al bucle
# de telemetría del WebSocket bridge. Dispara alertas de la Red Soberana
# (Discord + Mesh privada) cuando la estabilidad cae o hay keep-alive crítico.
_neural_monitor_task: Optional[asyncio.Task] = None


async def _neural_monitor_loop() -> None:
    last_alert = 0.0
    while True:
        try:
            vitals = collect_sys_vitals()
            tick = core.tick(vitals, alive=True)
            inst = tick.get("instability")
            ka = tick.get("keep_alive_fired", 0)
            stability = tick.get("stability", 1.0)
            # Difundir estabilidad neural a la Cabina Táctica Móvil (Mesh).
            await broadcast_mesh(
                {"type": "neural", "stability": round(stability, 4), "instability": bool(inst)}
            )
            now = asyncio.get_event_loop().time()
            if inst and (now - last_alert) > 30.0:
                msg = (
                    f"Neurona inestable (estabilidad={stability:.3f}, "
                    f"keep_alive={ka}). AURA manteniendo el sistema en línea."
                )
                discord_bridge.alert(msg)
                rocket_bridge.alert(msg)
                await broadcast_mesh_alert(msg)
                last_alert = now
        except Exception as exc:
            logger.error("Monitor de neurona falló: %s", exc)
        await asyncio.sleep(5.0)


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("AURA Backend starting up")
    await healer.start()
    # Red Soberana: arrancar Discord bridge, Rocket.Chat y monitor de neurona.
    discord_bridge.start()
    rocket_bridge.start()
    global _neural_monitor_task
    _neural_monitor_task = asyncio.create_task(
        _neural_monitor_loop(), name="neural-monitor"
    )

    # Autonomia Total: arrancar Cron proactivo (despertar + guardián salud).
    cron_scheduler.start()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    logger.info("AURA Backend shutting down")
    await healer.stop()
    try:
        await discord_bridge.stop()
    except Exception as exc:
        logger.error("Error deteniendo Discord bridge: %s", exc)
    try:
        await rocket_bridge.stop()
    except Exception as exc:
        logger.error("Error deteniendo Rocket.Chat bridge: %s", exc)
    try:
        await cron_scheduler.stop()
    except Exception as exc:
        logger.error("Error deteniendo Cron scheduler: %s", exc)
    global _neural_monitor_task
    if _neural_monitor_task is not None:
        _neural_monitor_task.cancel()
        try:
            await _neural_monitor_task
        except Exception:
            pass
        _neural_monitor_task = None
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
