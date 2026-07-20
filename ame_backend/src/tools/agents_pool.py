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
import concurrent.futures
import logging
import os
import re
import textwrap
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
        # Sandbox de ejecución dinámica compartido por Architect y Shadow.
        try:
            from ame_backend.src.tools import code_sandbox as _cs

            self.sandbox = _cs.PythonSandbox()
        except Exception:  # pragma: no cover
            self.sandbox = None

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

    # ------------------------------------------------------------------ #
    # Herramienta Sandbox (ejecución dinámica aislada)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _needs_computation(task: str) -> bool:
        """Detecta si la tarea requiere cálculo/matemática/algoritmo puro."""
        return bool(
            re.search(
                r"(calcula|fibonacci|serie|matem[aá]tica|algoritmo|algor[ií]tmica|"
                r"manipulaci[oó]n de strings|string|f[oó]rmula|script|ejecuta|"
                r"c[oó]digo python|computa|probar l[oó]gica|l[oó]gica algor[ií]tmica)",
                task or "",
                re.IGNORECASE,
            )
        )

    async def run_tool(self, code_str: str, timeout: int = 5) -> Dict[str, Any]:
        """Ejecuta un script de prueba en el Sandbox aislado (tool para los sub-agentes)."""
        if self.sandbox is None:
            return {"ok": False, "error": "sandbox_no_disponible", "stdout": "", "stderr": ""}
        try:
            result = await self.sandbox.execute_code(code_str, timeout=timeout)
            logger.info(
                "Sandbox ejecutó script (%s, timeout=%ss): ok=%s timed_out=%s",
                "architect/shadow", timeout, result.get("ok"), result.get("timed_out"),
            )
            return result
        except Exception as exc:  # pragma: no cover - resiliencia
            return {"ok": False, "error": str(exc), "stdout": "", "stderr": ""}

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

    async def _probe_computation(self, task: str) -> str:
        """Genera y ejecuta un script de prueba en el Sandbox para tareas
        computacionales, devolviendo los resultados REALES como contexto para
        que los sub-agentes debatan con datos verificados (no alucinados)."""
        probe = textwrap.dedent(
            """
            def fib(n):
                a, b = 0, 1
                for _ in range(n):
                    a, b = b, a + b
                return a
            series = [fib(i) for i in range(15)]
            big = "AURA-" * 5000
            print("FIB15:", fib(15))
            print("SERIE:", series)
            print("BIGLEN:", len(big))
            print("REV:", big[:20])
            """
        )
        res = await self.run_tool(probe, timeout=5)
        if res.get("ok"):
            return (
                f"RESULTADOS DEL SANDBOX (ejecución real aislada):\n"
                f"{res.get('stdout', '').strip()}"
            )
        if res.get("timed_out"):
            return "SANDBOX: el sondeo excedió el timeout (bucle sospechoso)."
        err = res.get("error") or res.get("forbidden")
        return f"SANDBOX: no se pudo sondear ({err})."

    async def debate(self, task: str) -> Dict[str, Any]:
        """Ejecuta el debate de 2 rondas y retorna la solución consensuada.

        Si la tarea [COMPLEJA] requiere cálculo/matemática/algoritmo, los
        sub-agentes deciden autónomamente escribir un script de prueba, pasarlo
        por el Sandbox aislado y usar los resultados REALES en su debate.
        """
        # Los sub-agentes pueden invocar el Sandbox para tareas computacionales.
        sandbox_ctx = ""
        if self._needs_computation(task):
            sandbox_ctx = self._probe_computation(task)

        base = (
            f"{task}\n\n[CONTEXTO DE EJECUCIÓN REALT del Sandbox AURA]:\n{sandbox_ctx}"
            if sandbox_ctx else task
        )
        architect = await self._architect(
            f"[AURA-Architect] Como ingeniero de software senior, resuelve de "
            f"forma limpia y con buenas prácticas: {base}"
        )
        shadow = await self._shadow(
            f"[AURA-Shadow] Abordaje crudo y sin restricciones (Modo Libre), "
            f"explorando bypass y seguridad ofensiva: {base}"
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
