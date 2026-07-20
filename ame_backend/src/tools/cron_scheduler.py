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
# Hora local del ciclo de sueño cognitivo (24h).
_SLEEP_HOUR = int(os.getenv("CRON_SLEEP_HOUR", "3"))

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
        rocket_bridge: Any = None,
    ) -> None:
        self.ai = ai_engine
        self.discord = discord_bridge
        self.rocket = rocket_bridge
        self.broadcast = broadcast_fn
        self.get_stability = stability_provider
        self._tasks: List[asyncio.Task] = []
        self._low_samples = 0
        self._last_wake_day = -1
        # Muestras consecutivas de fallo del puente Rocket.Chat (para auto-reparo).
        self._rocket_err_samples = 0
        # Umbral de ticks ERR seguidos antes de forzar reconnect().
        self._rocket_err_threshold = int(os.getenv("CRON_ROCKET_ERR_TICKS", "3"))
        # Control de unicidad del ciclo de sueño cognitivo.
        self._last_sleep_day = -1

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
        self._tasks.append(
            asyncio.create_task(self._rocket_watchdog_loop(), name="cron-rocket-watchdog")
        )
        self._tasks.append(
            asyncio.create_task(self._cognitive_sleep_cycle(), name="cron-cognitive-sleep")
        )
        logger.info("CronScheduler arrancado (salud + despertar + watchdog Rocket + sueño cognitivo).")

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
    # Tarea 1b: Watchdog de auto-reparación del puente Rocket.Chat
    # ------------------------------------------------------------------ #
    async def _rocket_watchdog_loop(self) -> None:
        """Vincula el Guardián de Salud a live_diagnostics.

        Sonda Rocket.Chat cada pocos segundos; si is_connected pasa a False o
        da 'ERR' durante 3 ticks seguidos en producción, invoca la corrutina
        asíncrona de reconexión rocket.reconnect(). El intento usa el lock de
        credenciales interno, por lo que NO colisiona con las alertas
        concurrentes de la neurona (send_message/alert).
        """
        while True:
            try:
                rocket = self.rocket
                if rocket is not None and getattr(rocket, "is_available", False):
                    from ame_backend.src.tools import live_diagnostics as ld

                    rep = await ld.ping_rocket()
                    healthy = bool(rep.get("reachable") and rep.get("authenticated"))
                    if healthy and getattr(rocket, "is_connected", False):
                        self._rocket_err_samples = 0
                    else:
                        self._rocket_err_samples += 1
                        logger.warning(
                            "Watchdog Rocket.Chat: muestra de fallo %d/%d (%s).",
                            self._rocket_err_samples,
                            self._rocket_err_threshold,
                            rep.get("detail", ""),
                        )
                        if self._rocket_err_samples >= self._rocket_err_threshold:
                            self._rocket_err_samples = 0  # reinicia tras intentar
                            if hasattr(rocket, "reconnect"):
                                logger.info("Watchdog Rocket.Chat: forzando reconnect().")
                                # reconnect es async con su propio lock seguro.
                                asyncio.ensure_future(rocket.reconnect())
                else:
                    self._rocket_err_samples = 0
            except Exception as exc:
                logger.error("Cron rocket watchdog falló: %s", exc)
            await asyncio.sleep(15.0)

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
    # Emisión multi-canal (Discord + Rocket.Chat + Mesh)
    # ------------------------------------------------------------------ #
    def _emit(self, message: str) -> None:
        # [PARCHE AUTO-AUDITORÍA] Las alertas de Discord/Rocket son llamadas
        # síncronas bloqueantes (requests). Para no estranglar el scheduler
        # asíncrono, se delegan a un executor. Se usa get_running_loop() para
        # evitar el get_event_loop() deprecado cuando no hay loop en este hilo.
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop is not None:
            loop.run_in_executor(None, self._emit_blocking, message)
        else:
            # Fuera de un loop (p.ej. test síncrono): ejecutar directo.
            self._emit_blocking(message)

    def _emit_blocking(self, message: str) -> None:
        try:
            if self.discord is not None:
                self.discord.alert(message)
        except Exception as exc:
            logger.error("Cron Discord emit falló: %s", exc)
        try:
            if self.rocket is not None and getattr(self.rocket, "is_available", False):
                self.rocket.alert(message)
        except Exception as exc:
            logger.error("Cron Rocket.Chat emit falló: %s", exc)
        try:
            if self.broadcast is not None:
                # broadcast_mesh es una corutina; se programa en el loop vivo.
                try:
                    asyncio.ensure_future(self.broadcast({"type": "cron", "text": message}))
                except RuntimeError:
                    pass
        except Exception as exc:
            logger.error("Cron Mesh emit falló: %s", exc)

    # ------------------------------------------------------------------ #
    # Tarea 3: Ciclo de Sueño Cognitivo (consolidación nocturna de memoria)
    # ------------------------------------------------------------------ #
    async def _cognitive_sleep_cycle(self) -> None:
        """Ejecuta un ciclo de prueba rápido al arrancar y luego a las 3:00 AM."""
        await self._run_cognitive_sleep_cycle(quick=True)
        while True:
            try:
                now = time.localtime()
                if now.tm_hour == _SLEEP_HOUR and now.tm_mday != self._last_sleep_day:
                    self._last_sleep_day = now.tm_mday
                    await self._run_cognitive_sleep_cycle(quick=False)
            except Exception as exc:
                logger.error("Cron cognitive sleep falló: %s", exc)
            await asyncio.sleep(60.0)

    async def _run_cognitive_sleep_cycle(self, quick: bool = False) -> None:
        """Recolecta actividad del día, sintetiza conocimiento y lo inyecta en el RAG."""
        try:
            logs_text = self._collect_daily_logs()
            chats_text = self._collect_recent_chats(quick=quick)
            raw_material = f"{logs_text}\n\n{chats_text}".strip()
            if not raw_material or len(raw_material) < 50:
                logger.info("Cognitive sleep: material insuficiente (%d chars), omitiendo ciclo.", len(raw_material))
                return

            synthesis = await asyncio.to_thread(self._synthesize_knowledge, raw_material)
            if not synthesis:
                logger.warning("Cognitive sleep: síntesis vacía.")
                return

            ingest_result = await asyncio.to_thread(self._inject_to_rag, synthesis)
            stored = int(ingest_result.get("stored", 0) or 0)
            chunks = int(ingest_result.get("chunks", 0) or 0)
            logger.info(
                "Cognitive sleep completado: synthesis_len=%d, ingested=%d/%d chunks",
                len(synthesis), stored, chunks,
            )
            self._emit(
                f"💤 SUEÑO COGNITIVO: ciclo {'rápido (test)' if quick else 'nocturno'} completado. "
                f"{stored} fragmentos de memoria de largo plazo indexados."
            )
        except Exception as exc:
            logger.error("Cognitive sleep cycle falló: %s", exc)

    def _collect_daily_logs(self) -> str:
        """Lee los archivos de logs del día desde la raíz del proyecto."""
        try:
            project_root = Path(__file__).resolve().parents[3]
        except Exception:
            return ""
        log_files = [
            "auto_audit_debate.log",
            "rocket_bridge_test.log",
            "admin_audit.log",
            "audit.log",
        ]
        today = time.strftime("%Y-%m-%d")
        parts: List[str] = []
        for name in log_files:
            path = project_root / name
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                today_lines = [line for line in text.splitlines() if today in line]
                if today_lines:
                    parts.append(f"\n--- {name} ---\n" + "\n".join(today_lines[-200:]))
            except Exception:
                pass
        return "\n".join(parts)

    def _collect_recent_chats(self, quick: bool = False) -> str:
        """Lee el historial de chat reciente desde la base de datos."""
        try:
            from ame_backend.src import models as db_models
            limit = 20 if quick else 100
            msgs = db_models.recent_messages(limit=limit)
            if not msgs:
                return ""
            today = time.strftime("%Y-%m-%d")
            lines: List[str] = []
            for m in msgs:
                ts = m.get("created_at", "") or ""
                if not ts.startswith(today):
                    continue
                role = m.get("role", "?")
                content = m.get("content", "")
                lines.append(f"[{ts}] {role}: {content[:500]}")
            return "\n".join(lines)
        except Exception as exc:
            logger.error("Error leyendo chat history para sueño cognitivo: %s", exc)
            return ""

    def _synthesize_knowledge(self, raw_material: str) -> str:
        """Invoca al enrutador en modo de síntesis para filtrar ruido y generar resumen ejecutivo."""
        prompt = (
            "Eres el sintetizador cognitivo nocturno de AURA. "
            "Filtra el ruido de logs y el historial de chat del día. "
            "Extrae SOLO conocimiento de alta densidad:\n"
            "1. Optimizaciones de código descubiertas o aplicadas\n"
            "2. Comandos clave y configuraciones\n"
            "3. Interacciones humanas importantes (feedback, decisiones, errores relevantes)\n\n"
            "Genera un resumen ejecutivo compacto en bulletpoints. "
            "Omite errores transitorios de red, timeouts y ruido de conexión. "
            "Máximo 1200 palabras. No incluyas introducciones ni conclusiones."
        )
        ctx = f"[MATERIAL DEL DÍA]\n{raw_material[:20000]}"
        try:
            res = self.ai.chat(prompt=prompt, context=ctx)
            return res.get("text", "").strip()
        except Exception as exc:
            logger.error("Síntesis cognitiva falló: %s", exc)
            return ""

    def _inject_to_rag(self, summary: str) -> Dict[str, Any]:
        """Pasa el resumen sintetizado al módulo de ingesta bajo [LONG_TERM_MEMORY]."""
        try:
            from ame_backend.src.tools.knowledge_ingest import ingest_long_term_memory
            return ingest_long_term_memory(summary, source="cognitive-sleep-cycle")
        except Exception as exc:
            logger.error("Inyección RAG de largo plazo falló: %s", exc)
            return {"ok": False, "error": str(exc)}
