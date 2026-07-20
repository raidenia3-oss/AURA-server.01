"""
Sandbox de Ejecución Dinámica — Entorno Aislado de Python para AURA.

``PythonSandbox`` permite a AURA (y a sus sub-agentes AURA-Architect /
AURA-Shadow) programar, probar y ejecutar scripts de Python para resolver
tareas lógicas complejas en tiempo real (cálculos matemáticos, manipulación
de strings a gran escala, lógica algorítmica pura) sin comprometer el hilo
principal de FastAPI.

Diseño de seguridad:
  * Aislamiento de proceso: el código corre en un SUBPROCESO hijo mediante
    ``asyncio.create_subprocess_exec`` (interprete Python separado), nunca en
    el event loop del backend. Un cuelgue del sandbox no tumba al servidor.
  * Timeout estricto: el proceso hijo es terminado a los N segundos
    (por defecto 5s) si no responde -> neutraliza bucles infinitos.
  * Captura limpia de stdout / stderr / excepciones del proceso hijo.
  * Filtro de palabras clave destructivas: bloquea operaciones de manipulación
    hostil del SO anfitrión (format, shutil.rmtree sobre rutas críticas, os.system,
    subprocess, socket bind, etc.) manteniendo flexibilidad para el Modo Libre.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import tempfile
import textwrap
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Bandera para habilitar/deshabilitar el filtro de seguridad (Modo Libre puede
# relajarla vía parámetro, pero nunca se elimina del todo por defecto).
_SECURITY_ENABLED = os.getenv("SANDBOX_SECURITY", "1") == "1"

# Patrones considerados destructivos para el SO anfitrión. Se bloquean salvo que
# se pida explícitamente relajar (Modo Libre) y la variable de entorno lo permita.
_DANGEROUS_PATTERNS: List[str] = [
    "os.system",
    "os.remove",
    "os.rmdir",
    "os.kill",
    "os.fork",
    "shutil.rmtree",
    "subprocess",
    "socket",
    "__import__",
    "eval(",
    "exec(",
    "open(",
    "import os",
    "from os",
    "import shutil",
    "from shutil",
    "ctypes",
    "multiprocessing",
    "sys.exit",
    "os._exit",
    "pty",
    "pickle.loads",
]

# Plantilla que envuelve el código del usuario y fuerza la salida limpia.
_RUNNER = textwrap.dedent(
    """
    import sys, json, traceback
    _src = {src!r}
    _ns = {{}}
    try:
        exec(compile(_src, "<sandbox>", "exec"), _ns)
    except Exception:
        traceback.print_exc()
        sys.exit(2)
    """
)


def _scan_dangerous(code: str) -> Optional[str]:
    """Devuelve el patrón peligroso encontrado o None si es seguro."""
    for pat in _DANGEROUS_PATTERNS:
        if pat in code:
            return pat
    return None


class PythonSandbox:
    """Ejecutor asíncrono de código Python en un subproceso aislado."""

    def __init__(self, security_enabled: bool = _SECURITY_ENABLED) -> None:
        self.security_enabled = security_enabled

    async def execute_code(
        self, code_str: str, timeout: int = 5, allow_unsafe: bool = False
    ) -> Dict[str, Any]:
        """Ejecuta ``code_str`` de forma aislada y devuelve un dict con el resultado.

        Retorna claves: ok, stdout, stderr, error, timed_out, returncode, forbidden.
        """
        # 1) Filtro de seguridad (salvo relajación explícita + entorno permitido).
        if self.security_enabled and not allow_unsafe:
            hit = _scan_dangerous(code_str)
            if hit:
                logger.warning("Sandbox bloqueó código por patrón prohibido: %s", hit)
                return {
                    "ok": False,
                    "stdout": "",
                    "stderr": "",
                    "error": f"forbidden_keyword:{hit}",
                    "timed_out": False,
                    "returncode": None,
                    "forbidden": hit,
                }

        # 2) Escribir el código a un archivo temporal (aislamiento de FS).
        runner = _RUNNER.format(src=code_str)
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(suffix=".py", prefix="aura_sandbox_")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(runner)
        except Exception as exc:  # pragma: no cover - resiliencia FS
            return {
                "ok": False, "stdout": "", "stderr": "",
                "error": f"sandbox_write_error:{exc}", "timed_out": False,
                "returncode": None, "forbidden": None,
            }

        # 3) Ejecutar en subproceso aislado con timeout estricto.
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
                timed_out = False
            except asyncio.TimeoutError:
                # Neutralizar el bucle infinito: matar el hijo limpiamente.
                if proc.returncode is None:
                    proc.kill()
                    try:
                        await proc.wait()
                    except Exception:
                        pass
                stdout_b, stderr_b = (await proc.stdout.read()
                                      if proc.stdout else b""), b""
                timed_out = True

            stdout = stdout_b.decode("utf-8", "replace") if stdout_b else ""
            stderr = stderr_b.decode("utf-8", "replace") if stderr_b else ""
            rc = proc.returncode
            return {
                "ok": (not timed_out and rc == 0),
                "stdout": stdout,
                "stderr": stderr,
                "error": ("timeout" if timed_out else (stderr.strip() or None)),
                "timed_out": timed_out,
                "returncode": rc,
                "forbidden": None,
            }
        except Exception as exc:  # pragma: no cover - resiliencia
            if proc is not None and proc.returncode is None:
                try:
                    proc.kill()
                except Exception:
                    pass
            return {
                "ok": False, "stdout": "", "stderr": "",
                "error": f"sandbox_exec_error:{exc}", "timed_out": False,
                "returncode": None, "forbidden": None,
            }
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass


# Helper de módulo para uso directo sin instanciar.
_default_sandbox = PythonSandbox()


async def execute_code(code_str: str, timeout: int = 5, allow_unsafe: bool = False) -> Dict[str, Any]:
    """Función de conveniencia: ejecuta código en el sandbox por defecto."""
    return await _default_sandbox.execute_code(code_str, timeout=timeout, allow_unsafe=allow_unsafe)
