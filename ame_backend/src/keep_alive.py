"""
keep_alive.py — Despertador de la instancia gratuita de Render.

La neurona evolutiva (NeuralCore) llama a ``trigger_keep_alive`` cuando
predice que el servidor entra en inactividad (riesgo de dormirse). Esto
hace un ping real a /health para mantener la instancia viva.
"""

from __future__ import annotations

import time
import urllib.request
from typing import Optional

DEFAULT_URL = "https://aura-backend-qwhl.onrender.com"
HEALTH_PATH = "/health"
TIMEOUT = 30


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


def trigger_keep_alive(base_url: str = DEFAULT_URL) -> Optional[float]:
    """Dispara actividad para evitar el cold-sleep de Render free."""
    return ping(base_url)
