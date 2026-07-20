"""
Ingesta de Conocimiento Senior — Expansión del Cerebro RAG.

``knowledge_ingest`` procesa bloques masivos de texto, fragmentos de
documentación (FastAPI/React) o URLs de manuales, los divide en chunks
optimizados, genera embeddings con ``GeminiEmbedder`` y los persiste en
``semantic_memory`` bajo el tag ``[KNOWLEDGE]``. Así AURA "aprende" de la
documentación oficial y enriquece el contexto del chat con conocimiento técnico.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

try:
    from ame_backend.src.neural_core import SemanticMemory, GeminiEmbedder
    from ame_backend.src import models
except Exception:  # pragma: no cover
    SemanticMemory = None  # type: ignore
    GeminiEmbedder = None  # type: ignore
    models = None  # type: ignore

try:
    from ame_backend.src.tools import browser as _browser
except Exception:  # pragma: no cover
    _browser = None

import logging

logger = logging.getLogger(__name__)

# Límites de seguridad / calidad.
_CHUNK_TOKENS = int(__import__("os").getenv("KNOWLEDGE_CHUNK_CHARS", "1200"))
_MAX_CHUNKS = int(__import__("os").getenv("KNOWLEDGE_MAX_CHUNKS", "200"))
_URL_MAX_CHARS = 20000

# Fuentes de conocimiento crítico para la Fase "Auto-Sustentación Cognitiva".
# Orden de importancia estratégica: Rocket.Chat (nueva plataforma) primero,
# luego asyncio (base de su puente asíncrono).
AUTO_INGEST_SOURCES = [
    {
        "url": "https://developer.rocket.chat/reference/api/rest-api/",
        "label": "Rocket.Chat REST API Reference",
        "topic": "rocket.chat.api",
    },
    {
        "url": "https://docs.rocket.chat/docs/create-a-bot/",
        "label": "Rocket.Chat Getting Started",
        "topic": "rocket.chat.setup",
    },
    {
        "url": "https://docs.python.org/3/library/asyncio.html",
        "label": "Python asyncio — Concurrency and Multithreading",
        "topic": "python.asyncio",
    },
    {
        "url": "https://docs.python.org/3/library/asyncio-task.html",
        "label": "Python asyncio Tasks and Coroutines Best Practices",
        "topic": "python.asyncio.task",
    },
]

# Bundle Senior de respaldo: conocimiento curado que se indexa SIEMPRE (incluso
# sin red) para garantizar que el cerebro RAG quede alimentado de forma 100%
# autónoma y tolerante a fallos de egress.
_AUTO_INGEST_FALLBACK = {
    "rocket.chat.api": (
        "[KNOWLEDGE][rocket.chat.api] Rocket.Chat REST API: autenticación vía "
        "POST /api/v1/login con {user, password} devuelve data.authToken y "
        "data.userId; usar headers X-Auth-Token y X-User-Id en llamadas. "
        "Canales: GET /api/v1/channels.info?roomName=NAME y channels.list; "
        "historial: GET /api/v1/channels.history?roomId=ID&count=N. Enviar "
        "mensajes: POST /api/v1/chat.postMessage {roomId, text}. Webhooks "
        "entrantes: POST a la URL del webhook con {text, username, channel}. "
        "Rate limits: usar backoff exponencial (Retry-After). Las operaciones "
        "bloqueantes de requests deben correr en run_in_executor para no "
        "bloquear el event loop de asyncio."
    ),
    "rocket.chat.setup": (
        "[KNOWLEDGE][rocket.chat.setup] Rocket.Chat self-hosted: el bot opera "
        "como usuario normal con permisos en el canal #aura-core. Para polling "
        "de mensajes usar channels.history con un last_ts incremental y "
        "dormir el loop con asyncio.sleep para no saturar la API. Las "
        "menciones se detectan por username o prefijo de comando. Mantener el "
        "authToken fresco; re-login si expira con 401."
    ),
    "python.asyncio": (
        "[KNOWLEDGE][python.asyncio] asyncio best practices: no bloquear el "
        "event loop con llamadas síncronas (requests, time.sleep, I/O pesada); "
        "usar async/await con httpx.AsyncClient o loop.run_in_executor. "
        "Crear tareas con asyncio.create_task (no esperarlas dentro del mismo "
        "frame si son background). Cancelar tareas en shutdown con "
        "task.cancel() y await para evitar corrupción. Usar "
        "asyncio.get_event_loop().time() para timers en vez de time.time()."
    ),
    "python.asyncio.task": (
        "[KNOWLEDGE][python.asyncio.task] asyncio coroutines: una función async "
        "no se ejecuta hasta ser awaited o pasada a create_task. Evitar "
        "concurrencia sobre estado mutable compartido sin Lock; usar "
        "asyncio.Lock para secciones críticas. asyncio.to_thread delega trabajo "
        "bloqueante a un thread del pool. Las excepciones en tareas no awaited "
        "se pierden (silent exceptions) salvo que se logueen en el task."
    ),
}


def _split_into_chunks(text: str, max_chars: int = _CHUNK_TOKENS) -> List[str]:
    """Divide el texto en chunks por párrafos/ojos de caracteres."""
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return []
    # Primero por saltos de bloque (doble salto o headings).
    blocks = re.split(r"\n\s*\n|(?=^#{1,6}\s)", text, flags=re.MULTILINE)
    chunks: List[str] = []
    buf = ""
    for blk in blocks:
        blk = blk.strip()
        if not blk:
            continue
        if len(blk) > max_chars:
            # Subdividir por oraciones.
            for sent in re.split(r"(?<=[.!:?])\s+", blk):
                if len(buf) + len(sent) > max_chars:
                    if buf:
                        chunks.append(buf.strip())
                    buf = sent
                else:
                    buf += " " + sent
        else:
            if len(buf) + len(blk) > max_chars:
                chunks.append(buf.strip())
                buf = blk
            else:
                buf = (buf + "\n\n" + blk).strip()
    if buf.strip():
        chunks.append(buf.strip())
    return chunks[:_MAX_CHUNKS]


def _fetch_url(url: str) -> str:
    if _browser is None:
        return ""
    try:
        return _browser.fetch_clean_text(url, timeout=20.0, max_chars=_URL_MAX_CHARS)
    except Exception:
        return ""


def ingest_text(text: str, source: str = "manual", kind: str = "[KNOWLEDGE]") -> Dict[str, Any]:
    """Ingesta un bloque de texto: chunking + embeddings + tag personalizable."""
    if SemanticMemory is None:
        return {"ok": False, "error": "semantic_memory_no_disponible"}
    chunks = _split_into_chunks(text)
    if not chunks:
        return {"ok": False, "error": "texto_vacio"}
    mem = SemanticMemory()
    stored = 0
    for i, chunk in enumerate(chunks):
        label = f"{kind} ({source}) p{i+1}/{len(chunks)}: {chunk}"
        try:
            if mem.remember(label, kind=kind) is not None:
                stored += 1
        except Exception:
            pass
    return {
        "ok": True,
        "chunks": len(chunks),
        "stored": stored,
        "source": source,
    }


def ingest_long_term_memory(text: str, source: str = "cognitive-sleep") -> Dict[str, Any]:
    """Ingesta memoria de largo plazo: chunking + embeddings + [LONG_TERM_MEMORY]."""
    return ingest_text(text, source=source, kind="[LONG_TERM_MEMORY]")


def ingest_url(url: str) -> Dict[str, Any]:
    """Ingesta la documentación de una URL de manual."""
    content = _fetch_url(url)
    if not content:
        return {"ok": False, "error": "no_se_pudo_raspar", "url": url}
    return ingest_text(content, source=url)


def ingest(payload: dict) -> Dict[str, Any]:
    """Punto de entrada del endpoint. Acepta text/code o url."""
    if payload.get("url"):
        return ingest_url(payload["url"])
    text = payload.get("text") or payload.get("code") or ""
    if not text:
        return {"ok": False, "error": "falta_text_o_url"}
    source = payload.get("source", "manual")
    return ingest_text(text, source=source)


def auto_ingest_critical(sources: Optional[List[dict]] = None) -> Dict[str, Any]:
    """Auto-sustentación cognitiva: raspa + indexa conocimiento crítico.

    Usa ``browser.py`` para raspar la documentación oficial de Rocket.Chat y las
    mejores prácticas de ``asyncio`` de Python, y la pasa por ``ingest_text``
    (el mismo camino del endpoint ``POST /api/knowledge/ingest``) para indexarla
    en la memoria vectorial bajo el tag ``[KNOWLEDGE]``.

    Diseño tolerante a fallos: si una URL no raspable (sin red / bloqueada),
    se usa el bundle Senior de respaldo para ese ``topic`` de modo que el RAG
    siempre queda alimentado. Devuelve un reporte detallado por fuente.
    """
    sources = sources or AUTO_INGEST_SOURCES
    report: List[Dict[str, Any]] = []
    total_stored = 0
    total_chunks = 0
    scraped = 0
    fallback = 0

    for src in sources:
        url = src.get("url", "")
        topic = src.get("topic", "misc")
        label = src.get("label", url)
        # 1) Intentar raspar con las garras web.
        content = _fetch_url(url)
        if content:
            res = ingest_text(content, source=f"auto:{topic}:{url}")
            mode = "scrape"
            scraped += 1
        else:
            # 2) Fallback Senior curado (sin red).
            bundle = _AUTO_INGEST_FALLBACK.get(topic)
            if bundle:
                res = ingest_text(bundle, source=f"auto-fallback:{topic}")
                mode = "fallback"
                fallback += 1
            else:
                res = {"ok": False, "error": "sin_contenido_ni_fallback", "stored": 0, "chunks": 0}
                mode = "none"
        chunks = int(res.get("chunks", 0) or 0)
        stored = int(res.get("stored", 0) or 0)
        total_chunks += chunks
        total_stored += stored
        report.append(
            {
                "label": label,
                "url": url,
                "topic": topic,
                "mode": mode,
                "ok": bool(res.get("ok")),
                "chunks": chunks,
                "stored": stored,
            }
        )
        logger.info(
            "Auto-ingesta [%s] %s: mode=%s chunks=%s stored=%s",
            topic, label, mode, chunks, stored,
        )

    return {
        "ok": True,
        "phase": "auto-sustentacion-cognitiva",
        "sources": len(sources),
        "scraped": scraped,
        "fallback": fallback,
        "total_chunks": total_chunks,
        "total_stored": total_stored,
        "report": report,
    }
