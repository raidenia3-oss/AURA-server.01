"""
keep_alive.py — Despertador de la instancia gratuita de Render.

La neurona evolutiva (NeuralCore) llama a ``trigger_keep_alive`` cuando
predice que el servidor entra en inactividad (riesgo de dormirse). Esto
hace un ping real a /health para mantener la instancia viva.
"""

from __future__ import annotations

import os
import time
import urllib.request
from typing import Optional

DEFAULT_URL = os.getenv("RENDER_URL", "https://aura-backend-qwhl.onrender.com")
HEALTH_PATH = "/health"
TIMEOUT = 30

# Nodo espejo (Koyeb/Fly) que debe mantenerse despierto si este nodo cae.
MIRROR_NODE_URL = os.getenv("MIRROR_NODE_URL")


def ping(base_url: str = DEFAULT_URL) -> Optional[float]:
    """Hace un ping a /health y retorna la latencia en ms (o None)."""
    url = base_url.rstrip("/") + HEALTH_PATH
    req = urllib.request.Request(url, headers={"User-Agent": "aura-keepalive/1.0"})
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            elapsed = (time.perf_counter() - start) * 1000
            return elapsed if resp.getcode() == 200 else None
    except Exception:
        return None


def _relay_to_mirror() -> bool:
    """Envía señal de relevo al nodo espejo para mantener la red despierta."""
    if not MIRROR_NODE_URL:
        return False
    try:
        url = MIRROR_NODE_URL.rstrip("/") + HEALTH_PATH
        req = urllib.request.Request(
            url, headers={"User-Agent": "aura-mirror-relay/1.0"}
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.getcode() == 200
    except Exception as exc:  # pragma: no cover
        print(f"[keep_alive] relevo a espejo falló: {exc}")
        return False


def trigger_keep_alive(base_url: str = DEFAULT_URL) -> Optional[float]:
    """Dispara actividad para evitar el cold-sleep de Render free.

    Si el ping local falla (servidor entrando en suspensión), envía una
    señal de relevo al nodo espejo para mantener la red soberana despierta.
    """
    latency = ping(base_url)
    if latency is None and MIRROR_NODE_URL:
        _relay_to_mirror()
    return latency
