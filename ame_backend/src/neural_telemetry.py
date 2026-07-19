"""
Telemetría de Herramientas para la Neurona Artificial.

Acumula señales de las nuevas capacidades de AURA (RAG semántico, enrutador
multi-modelo, Workspace Operator) y las expone normalizadas para que
``AuraPerceptron`` pueda usarlas como entradas adicionales. Esto hace que la
neurona sea más inteligente y predictiva: ya no solo ve latencia/memoria,
sino también "qué tan útil y segura está siendo la operación del sistema".
"""

from __future__ import annotations

import threading
import time
from typing import Dict

_lock = threading.Lock()

# Contadores crudos (ventana deslizante simple).
_stats = {
    "rag_queries": 0,
    "rag_hits": 0,
    "router_calls": 0,
    "router_errors": 0,
    "workspace_ops": 0,
    "workspace_blocks": 0,
    "tool_calls": 0,
    "window_start": time.time(),
}

_WINDOW_SECONDS = 120.0


def _reset_if_expired() -> None:
    now = time.time()
    if now - _stats["window_start"] > _WINDOW_SECONDS:
        for k in (
            "rag_queries",
            "rag_hits",
            "router_calls",
            "router_errors",
            "workspace_ops",
            "workspace_blocks",
            "tool_calls",
        ):
            _stats[k] = 0
        _stats["window_start"] = now


def record_rag(query: str, hits: int) -> None:
    with _lock:
        _reset_if_expired()
        _stats["rag_queries"] += 1
        if hits > 0:
            _stats["rag_hits"] += 1


def record_router(call: bool, error: bool) -> None:
    with _lock:
        _reset_if_expired()
        _stats["router_calls"] += 1
        if error:
            _stats["router_errors"] += 1


def record_workspace(op: bool, blocked: bool) -> None:
    with _lock:
        _reset_if_expired()
        if op:
            _stats["workspace_ops"] += 1
        if blocked:
            _stats["workspace_blocks"] += 1


def record_tool_call() -> None:
    with _lock:
        _reset_if_expired()
        _stats["tool_calls"] += 1


def snapshot() -> Dict[str, float]:
    """Devuelve señales normalizadas 0..1 para la neurona."""
    with _lock:
        _reset_if_expired()
        q = max(1, _stats["rag_queries"])
        rag_hit_rate = _stats["rag_hits"] / q  # 0..1 (1 = siempre acierta)
        rc = max(1, _stats["router_calls"])
        router_err_rate = _stats["router_errors"] / rc  # 0..1 (1 = siempre falla)
        # Traversal bloqueado: señal de seguridad activa (0..1 por ventana).
        block_rate = min(1.0, _stats["workspace_blocks"] / 5.0)
        # Actividad de herramientas: refleja un sistema "vivo y operando".
        tool_activity = min(1.0, (_stats["workspace_ops"] + _stats["tool_calls"]) / 10.0)
        return {
            "rag_hit_rate": rag_hit_rate,
            "router_err_rate": router_err_rate,
            "workspace_block_rate": block_rate,
            "tool_activity": tool_activity,
        }
