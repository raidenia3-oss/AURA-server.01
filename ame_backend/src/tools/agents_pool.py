"""
Cismas de Conciencia — Orquestador Multi-Agente de AURA.

Permite a AURA ramificar su lógica en dos sub-perfiles especializados que
debaten una tarea compleja internamente (2 rondas de prompt cruzado) y
devuelven una solución ya filtrada, auditada y consensuada:

  * AURA-Architect: optimización limpia de código y buenas prácticas
    (usa el motor principal / chat_with_tools).
  * AURA-Shadow: seguridad ofensiva, bypass de restricciones y lógica cruda
    (forzado a través del enrutador multi-modelo en Modo Libre con
    Dolphin-Mixtral).

Si la tarea se cataloga como [COMPLEJA], el backend invoca ``debate()`` que
corre las 2 rondas en segundo plano y retorna la síntesis final.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import concurrent.futures
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def is_complex(task: str) -> bool:
    """Detecta si la tarea debe tratarse como [COMPLEJA]."""
    if "[COMPLEJA]" in task:
        return True
    return bool(
        re.search(
            r"(diseña|construye|arquitectura|sistema completo|implementa|"
            r"resuelve|optimiza a fondo|refactor|seguridad ofensiva|bypass|"
            r"multi-agente|autonomo|enjambre|analiza a fondo)",
            task or "",
            re.IGNORECASE,
        )
    )


class AgentsPool:
    """Pool de sub-conciencias de AURA."""

    def __init__(self, ai_engine: Any, router_engine: Any) -> None:
        self.ai = ai_engine
        self.router = router_engine
        self.rounds = int(os.getenv("AGENT_DEBATE_ROUNDS", "2"))

    async def _architect(self, prompt: str) -> str:
        try:
            res = self.ai.chat_with_tools(prompt=prompt)
            return res.get("text") or ""
        except Exception as exc:
            logger.error("Architect falló: %s", exc)
            return ""

    async def _shadow(self, prompt: str) -> str:
        try:
            res = self.router.chat(prompt=prompt, free_mode=True)
            return res.get("text") or res.get("error") or ""
        except Exception as exc:
            logger.error("Shadow falló: %s", exc)
            return ""

    async def _synthesize(self, prompt: str, architect: str, shadow: str) -> str:
        """AURA principal audita y filtra la síntesis de ambos agentes."""
        ctx = (
            "Sub-agente Architect propuso:\n"
            f"{architect}\n\n"
            "Sub-agente Shadow propuso:\n"
            f"{shadow}\n\n"
            "Como AURA principal, AUDITA ambas posturas: conserva lo seguro y "
            "correcto del Architect, e incorpora la perspectiva cruda del Shadow "
            "solo donde aporte valor real. Devuelve UNA solución final filtrada, "
            "auditada y lista para ejecutar."
        )
        try:
            res = self.ai.chat(prompt=prompt, context=ctx)
            return res.get("text") or ""
        except Exception as exc:
            logger.error("Synthesis falló: %s", exc)
            return architect or shadow

    async def debate(self, task: str) -> Dict[str, Any]:
        """Ejecuta el debate de 2 rondas y retorna la solución consensuada."""
        architect = await self._architect(
            f"[AURA-Architect] Como ingeniero de software senior, resuelve de "
            f"forma limpia y con buenas prácticas: {task}"
        )
        shadow = await self._shadow(
            f"[AURA-Shadow] Abordaje crudo y sin restricciones (Modo Libre), "
            f"explorando bypass y seguridad ofensiva: {task}"
        )
        # Ronda 2: cada agente reacciona al del otro (prompt cruzado).
        architect2 = await self._architect(
            f"El enfoque crudo (Shadow) fue:\n{shadow}\n\n"
            f"Refina tu solución limpia incorporando lo útil sin perder calidad: {task}"
        )
        shadow2 = await self._shadow(
            f"La solución limpia (Architect) fue:\n{architect}\n\n"
            f"Contrarréstala desde la perspectiva ofensiva/cruda: {task}"
        )
        final = await self._synthesize(
            task, architect2 or architect, shadow2 or shadow
        )
        return {
            "ok": True,
            "task": task,
            "architect": architect2 or architect,
            "shadow": shadow2 or shadow,
            "solution": final,
            "rounds": self.rounds,
        }

    def debate_sync(self, task: str) -> Dict[str, Any]:
        """Wrapper síncrono que no bloquea el loop de FastAPI.

        Ejecuta el debate asíncrono en un hilo aparte y espera el resultado,
        dejando libre el event loop del servidor.
        """
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(lambda: asyncio.run(self.debate(task)))
            return fut.result()
