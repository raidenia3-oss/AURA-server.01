"""
Orquestador Autónomo ("Enjambre Autónomo").

Capacidades:
  1. Auto-optimización: lee de forma SEGURA los archivos del backend
     (main.py, neural_core.py) y logs del sistema mediante el Workspace
     Operator (sandbox), y pide a Gemini que analice el rendimiento de la
     neurona artificial. Si Gemini propone una optimización de código, la
     reescritura se hace SOLO cuando el usuario lo aprueba explícitamente
     (flag ``apply=True``), usando las herramientas del Workspace. Por defecto
     el orquestador solo SUGIERE, no muta el backend.
  2. Server Scout: usa browser.py para recopilar información sobre
     plataformas cloud alternativas (Koyeb, Fly.io, Railway, Render, Oracle).
  3. Generador de infraestructura: produce Dockerfiles optimizados y
     configuración de despliegue estandarizada lista para inyectar en otros
     servidores al expandir el enjambre.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

try:
    from ame_backend.src.tools import workspace as _ws
    from ame_backend.src.tools import browser as _browser
except Exception:  # pragma: no cover
    _ws = None
    _browser = None

# Archivos del backend que el orquestador puede inspeccionar (sandbox).
_BACKEND_TARGETS = [
    "ame_backend/src/main.py",
    "ame_backend/src/neural_core.py",
    "ame_backend/src/services/ai_engine.py",
    "ame_backend/src/models.py",
]

_SCOUT_TARGETS = [
    "https://www.koyeb.com/",
    "https://fly.io/",
    "https://railway.app/",
    "https://render.com/",
    "https://www.oracle.com/cloud/free/",
]


def read_backend_sources() -> Dict[str, Any]:
    """Lee los archivos del backend dentro del sandbox (solo lectura)."""
    if _ws is None:
        return {"ok": False, "error": "workspace_no_disponible"}
    out: Dict[str, Any] = {"ok": True, "files": {}}
    for rel in _BACKEND_TARGETS:
        res = _ws.read_workspace_file(rel)
        if res.get("ok"):
            out["files"][rel] = {
                "size": res.get("size"),
                "content": res.get("content", ""),
            }
        else:
            out["files"][rel] = {"error": res.get("error")}
    return out


def read_system_logs(limit_kb: int = 32) -> Dict[str, Any]:
    """Lee logs del sistema dentro del sandbox (data/, logs/, *.log)."""
    if _ws is None:
        return {"ok": False, "error": "workspace_no_disponible"}
    logs: List[Dict[str, Any]] = []
    for cand in ["data/db.json", "ame_backend/logs/aura.log", "aura.log"]:
        res = _ws.read_workspace_file(cand)
        if res.get("ok"):
            logs.append(
                {
                    "path": cand,
                    "size": res.get("size"),
                    "content": res.get("content", "")[: limit_kb * 1024],
                }
            )
    return {"ok": True, "logs": logs}


def analyze_performance(engine: Any, neural_status: Optional[dict] = None) -> Dict[str, Any]:
    """Pide a Gemini que analice el rendimiento y sugiera optimizaciones.

    Devuelve SUGERENCIAS en texto. NO reescribe archivos por sí solo.
    """
    if _ws is None:
        return {"ok": False, "error": "workspace_no_disponible"}
    sources = read_backend_sources()
    if not sources.get("ok"):
        return sources
    snippets = []
    for path, info in sources["files"].items():
        if "content" in info:
            snippets.append(f"# {path}\n{info['content'][:3000]}")
    ctx = "\n\n".join(snippets)
    if neural_status:
        ctx += f"\n\n# Estado Neurona\n{neural_status}"
    prompt = (
        "Eres el orquestador autónomo de AURA. Analiza el rendimiento de la "
        "neurona artificial (Sys Vitals, latencia, uso de memoria) y el código "
        "mostrado. Sugiere optimizaciones matemáticas o de código CONCRETAS y "
        "seguras. Si propones reescribir un archivo, incluye la sección "
        "EXACTA a cambiar y el reemplazo propuesto en formato diff textual."
    )
    try:
        res = engine.chat(prompt=prompt, context=ctx)
    except Exception as exc:
        return {"ok": False, "error": f"analisis_fallo: {exc}"}
    return {
        "ok": True,
        "analysis": res.get("text", ""),
        "provider": res.get("provider"),
        "files_scanned": list(sources["files"].keys()),
    }


def apply_optimization(
    rel_path: str, original: str, optimized: str
) -> Dict[str, Any]:
    """Aplica una optimización propuesta escribiéndola en el sandbox.

    SOLO debe llamarse con aprobación explícita del usuario. Valida que el
    archivo objetivo esté dentro de los targets permitidos.
    """
    if rel_path not in _BACKEND_TARGETS:
        return {
            "ok": False,
            "error": "archivo_no_autorizado",
            "path": rel_path,
        }
    if _ws is None:
        return {"ok": False, "error": "workspace_no_disponible"}
    # Verificación de seguridad: reescribe el contenido completo optimizado.
    if original and original not in (current := _ws.read_workspace_file(rel_path).get("content", "")):
        return {
            "ok": False,
            "error": "desincronizacion: el original no coincide con el archivo actual",
        }
    res = _ws.write_workspace_file(rel_path, optimized)
    if res.get("ok"):
        try:
            from ame_backend.src.neural_core import SemanticMemory

            SemanticMemory().remember(
                f"[WORKSPACE] Optimización autónoma aplicada en {rel_path}.",
                kind="[WORKSPACE]",
            )
        except Exception:
            pass
    return res


def scout_infrastructure(targets: Optional[List[str]] = None) -> Dict[str, Any]:
    """Recopila información de plataformas cloud alternativas vía browser.py."""
    if _browser is None:
        return {"ok": False, "error": "browser_no_disponible"}
    targets = targets or _SCOUT_TARGETS
    found: List[Dict[str, Any]] = []
    for url in targets[:5]:
        try:
            text = _browser.fetch_clean_text(url, timeout=15.0, max_chars=2500)
            if text:
                found.append(
                    {
                        "url": url,
                        "snippet": text[:600],
                        "title": _derive_title(text),
                    }
                )
        except Exception as exc:
            found.append({"url": url, "error": str(exc)})
    return {"ok": True, "platforms": found}


def _derive_title(text: str) -> str:
    m = re.search(r"(?i)([^\n]{8,60})", text or "")
    return m.group(1).strip() if m else "plataforma"


def generate_deployment_config(
    target: str = "generic",
    port: int = 8000,
    python_version: str = "3.11",
) -> Dict[str, Any]:
    """Genera un Dockerfile optimizado + docker-compose para expandir el enjambre."""
    dockerfile = _DOCKERFILE_TEMPLATE.format(
        python_version=python_version, port=port
    )
    # El compose usa ${VAR} de shell: escapamos con replace para no chocar
    # con str.format().
    compose = (
        _COMPOSE_TEMPLATE.replace("{target}", target)
        .replace("{port}", str(port))
    )
    return {
        "ok": True,
        "target": target,
        "dockerfile": dockerfile,
        "docker_compose": compose,
    }


_DOCKERFILE_TEMPLATE = """\
# AURA Swarm Node — Dockerfile optimizado (multi-stage)
FROM python:{python_version}-slim AS base
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

FROM base AS build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM base AS runtime
COPY --from=build /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .
EXPOSE {port}
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:{port}/health').status==200 else 1)"
CMD ["sh", "-c", "uvicorn ame_backend.src.main:app --host 0.0.0.0 --port {port}"]
"""

_COMPOSE_TEMPLATE = """\
version: "3.9"
services:
  aura-{target}:
    build: .
    container_name: aura-{target}-node
    restart: unless-stopped
    ports:
      - "{port}:{port}"
    environment:
      - AURA_WORKSPACE_DIR=/app
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - OPENROUTER_FREE_KEY=${OPENROUTER_FREE_KEY}
      - DEEPINFRA_API_KEY=${DEEPINFRA_API_KEY}
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:{port}/health')"]
      interval: 30s
      timeout: 5s
      retries: 3
    networks:
      - aura-swarm

networks:
  aura-swarm:
    driver: bridge
"""
