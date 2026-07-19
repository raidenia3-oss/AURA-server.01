"""
El Despertar del Cron — Autonomía proactiva de AURA.

Programador de tareas asíncrono en segundo plano (asyncio). AURA actúa por
iniciativa propia sin intervención del usuario:

  1. Despertar matutino: cada mañana raspia las 3 noticias tecnológicas más
     críticas del día (browser.py), empaqueta un reporte breve y lo difunde
     por Discord (DiscordBridge) y por broadcast al WebSocket de la Mesh Móvil.
  2. Guardián de salud: vigila la telemetría de la neurona de 8 entradas; si la
     estabilidad cae por debajo de 0.4 de forma sostenida, dispara una alerta
     de salud automática (sin intervención del usuario).

El scheduler corre en sus propios background tasks y NO bloquea el event loop
de FastAPI ni el bucle de telemetría de la neurona.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)

# Umbral de estabilidad para alerta de salud sostenida.
_HEALTH_STABILITY_FLOOR = float(os.getenv("CRON_HEALTH_FLOOR", "0.4"))
# Ventana de muestras bajo umbral antes de alertar (evita falsos positivos).
_HEALTH_SUSTAIN_SAMPLES = int(os.getenv("CRON_HEALTH_SUSTAIN", "3"))
# Hora local de despertar (24h).
_WAKE_HOUR = int(os.getenv("CRON_WAKE_HOUR", "7"))

_NEWS_SOURCES = [
    "https://techcrunch.com/",
    "https://www.theverge.com/",
    "https://arstechnica.com/",
]


class CronScheduler:
    """Orquesta las tareas proactivas de AURA en background."""

    def __init__(
        self,
        ai_engine: Any,
        discord_bridge: Any,
        broadcast_fn: Optional[Callable[[dict], Any]] = None,
        stability_provider: Optional[Callable[[], float]] = None,
    ) -> None:
        self.ai = ai_engine
        self.discord = discord_bridge
        self.broadcast = broadcast_fn
        self.get_stability = stability_provider
        self._tasks: List[asyncio.Task] = []
        self._low_samples = 0
        self._last_wake_day = -1

    # ------------------------------------------------------------------ #
    # Ciclo de vida
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        if self._tasks:
            return
        self._tasks.append(
            asyncio.create_task(self._health_guard_loop(), name="cron-health")
        )
        self._tasks.append(
            asyncio.create_task(self._daily_wake_loop(), name="cron-wake")
        )
        logger.info("CronScheduler arrancado (salud + despertar).")

    async def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except Exception:
                pass
        self._tasks.clear()

    # ------------------------------------------------------------------ #
    # Tarea 1: Guardian de salud (estabilidad < 0.4 sostenida)
    # ------------------------------------------------------------------ #
    async def _health_guard_loop(self) -> None:
        while True:
            try:
                if self.get_stability is not None:
                    stab = self.get_stability()
                    if stab < _HEALTH_STABILITY_FLOOR:
                        self._low_samples += 1
                    else:
                        self._low_samples = 0
                    if self._low_samples >= _HEALTH_SUSTAIN_SAMPLES:
                        msg = (
                            f"⚠️ SALUD: estabilidad sostenida baja "
                            f"({stab:.3f} < {_HEALTH_STABILITY_FLOOR}). "
                            f"AURA en modo de preservación."
                        )
                        self._emit(msg)
                        self._low_samples = 0  # reinicia para no spammezar
            except Exception as exc:
                logger.error("Cron health guard falló: %s", exc)
            await asyncio.sleep(10.0)

    # ------------------------------------------------------------------ #
    # Tarea 2: Despertar matutino con noticias críticas
    # ------------------------------------------------------------------ #
    async def _daily_wake_loop(self) -> None:
        while True:
            try:
                now = time.localtime()
                if now.tm_hour == _WAKE_HOUR and now.tm_mday != self._last_wake_day:
                    self._last_wake_day = now.tm_mday
                    report = await self._build_morning_report()
                    if report:
                        self._emit(f"☀️ DESPERTAR DE AURA\n{report}")
            except Exception as exc:
                logger.error("Cron wake falló: %s", exc)
            await asyncio.sleep(60.0)

    async def _build_morning_report(self) -> Optional[str]:
        """Raspa 3 noticias críticas y pide a Gemini un reporte breve."""
        try:
            from ame_backend.src.tools import browser as _browser
        except Exception:  # pragma: no cover
            _browser = None
        headlines: List[str] = []
        if _browser is not None:
            for url in _NEWS_SOURCES:
                try:
                    text = _browser.fetch_clean_text(url, timeout=12.0, max_chars=1500)
                    if text:
                        # Toma la primera línea no vacía como titular.
                        first = next(
                            (l.strip() for l in text.splitlines() if l.strip()), ""
                        )
                        if first:
                            headlines.append(f"• {first[:140]}")
                except Exception:
                    pass
                if len(headlines) >= 3:
                    break
        if not headlines:
            return "AURA despierta. Sin titulares disponibles en este momento."
        digest = "\n".join(headlines[:3])
        # Resumen ejecutivo con Gemini (mejor-effort).
        try:
            res = self.ai.chat(
                prompt=(
                    "Resume en 2 líneas máximo por qué estas 3 noticias "
                    "tecnológicas importan para un sistema autónomo:"
                    f"\n{digest}"
                )
            )
            summary = res.get("text", "")
        except Exception:
            summary = ""
        out = f"Noticias críticas:\n{digest}"
        if summary:
            out += f"\n\nAnálisis AURA:\n{summary}"
        return out

    # ------------------------------------------------------------------ #
    # Emisión multi-canal (Discord + Mesh)
    # ------------------------------------------------------------------ #
    def _emit(self, message: str) -> None:
        try:
            if self.discord is not None:
                self.discord.alert(message)
        except Exception as exc:
            logger.error("Cron Discord emit falló: %s", exc)
        try:
            if self.broadcast is not None:
                coro = self.broadcast({"type": "cron", "text": message})
                # Si es corutina, programarla en el loop actual.
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.ensure_future(coro)
                    else:
                        asyncio.run(coro)
                except RuntimeError:
                    asyncio.ensure_future(coro)
        except Exception as exc:
            logger.error("Cron Mesh emit falló: %s", exc)
