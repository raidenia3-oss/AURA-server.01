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

# Límites de seguridad / calidad.
_CHUNK_TOKENS = int(__import__("os").getenv("KNOWLEDGE_CHUNK_CHARS", "1200"))
_MAX_CHUNKS = int(__import__("os").getenv("KNOWLEDGE_MAX_CHUNKS", "200"))
_URL_MAX_CHARS = 20000


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


def ingest_text(text: str, source: str = "manual") -> Dict[str, Any]:
    """Ingesta un bloque de texto: chunking + embeddings + [KNOWLEDGE]."""
    if SemanticMemory is None:
        return {"ok": False, "error": "semantic_memory_no_disponible"}
    chunks = _split_into_chunks(text)
    if not chunks:
        return {"ok": False, "error": "texto_vacio"}
    mem = SemanticMemory()
    stored = 0
    for i, chunk in enumerate(chunks):
        label = f"[KNOWLEDGE] ({source}) p{i+1}/{len(chunks)}: {chunk}"
        try:
            if mem.remember(label, kind="[KNOWLEDGE]") is not None:
                stored += 1
        except Exception:
            pass
    return {
        "ok": True,
        "chunks": len(chunks),
        "stored": stored,
        "source": source,
    }


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
