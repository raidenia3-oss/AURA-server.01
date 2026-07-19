"""
Módulo Operador de Workspace ("manos" locales de AURA).

Expone operaciones de archivo SEGURAS y acotadas a un sandbox estricto
(AURA_WORKSPACE_DIR, por defecto la raíz del repositorio). Todo path se
resuelve y se verifica que quede dentro del sandbox antes de cualquier
lectura/escritura, bloqueando path traversal (../) y symlinks que salgan
del directorio permitido. Así AURA puede operar código sin tocar el resto
del sistema operativo.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Sandbox base: variable de entorno o raíz del repo (2 niveles arriba de
# este archivo: ame_backend/src/tools -> raíz del proyecto AURA).
_DEFAULT_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE_ROOT = Path(
    os.getenv("AURA_WORKSPACE_DIR", str(_DEFAULT_ROOT))
).resolve()

# Límites de seguridad.
_MAX_READ_BYTES = int(os.getenv("AURA_WORKSPACE_MAX_READ_BYTES", str(2 * 1024 * 1024)))
_MAX_WRITE_BYTES = int(os.getenv("AURA_WORKSPACE_MAX_WRITE_BYTES", str(512 * 1024)))
_ALLOWED_WRITE_SUFFIXES = {
    ".txt", ".md", ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml",
    ".yml", ".csv", ".log", ".html", ".css", ".sh", ".bat", ".cfg", ".toml",
    ".ini", ".env", ".gitignore", ".lock",
}


def _safe_path(rel_path: str) -> Path:
    """Resuelve ``rel_path`` dentro del sandbox y valida que no salga de él."""
    if not rel_path:
        raise ValueError("Ruta vacía no permitida.")
    # Bloquea separadores absolutos y traversal explícito.
    if rel_path.startswith(("/", "\\")) or os.path.isabs(rel_path):
        raise ValueError("Rutas absolutas no permitidas en el sandbox.")
    cand = (WORKSPACE_ROOT / rel_path).resolve()
    # Path traversal: el resultado debe quedar bajo WORKSPACE_ROOT.
    try:
        cand.relative_to(WORKSPACE_ROOT)
    except ValueError:
        raise ValueError(
            f"Acceso denegado: '{rel_path}' sale del workspace sandbox."
        )
    # Symlink que apunte afuera del sandbox.
    if cand.is_symlink():
        real = cand.resolve(strict=False)
        try:
            real.relative_to(WORKSPACE_ROOT)
        except ValueError:
            raise ValueError("Enlaces simbólicos fuera del sandbox no permitidos.")
    return cand


def read_workspace_file(rel_path: str, max_bytes: Optional[int] = None) -> Dict[str, Any]:
    """Lee un archivo del sandbox. Devuelve contenido, tamaño y encoding."""
    try:
        path = _safe_path(rel_path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "path": rel_path}
    if not path.exists():
        return {"ok": False, "error": "archivo_no_encontrado", "path": rel_path}
    if not path.is_file():
        return {"ok": False, "error": "no_es_archivo", "path": rel_path}
    size = path.stat().st_size
    limit = max_bytes or _MAX_READ_BYTES
    if size > limit:
        return {
            "ok": False,
            "error": "archivo_demasiado_grande",
            "path": rel_path,
            "size": size,
            "max_bytes": limit,
        }
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": f"lectura_fallo: {exc}", "path": rel_path}
    return {
        "ok": True,
        "path": rel_path,
        "size": size,
        "content": text,
    }


def write_workspace_file(
    rel_path: str, content: str, append: bool = False
) -> Dict[str, Any]:
    """Escribe (o anexa) contenido a un archivo dentro del sandbox."""
    try:
        path = _safe_path(rel_path)
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "path": rel_path}
    suffix = path.suffix.lower()
    if suffix and suffix not in _ALLOWED_WRITE_SUFFIXES:
        return {
            "ok": False,
            "error": f"extension_no_permitida: {suffix}",
            "path": rel_path,
        }
    if len(content.encode("utf-8")) > _MAX_WRITE_BYTES:
        return {
            "ok": False,
            "error": "contenido_demasiado_grande",
            "path": rel_path,
            "max_bytes": _MAX_WRITE_BYTES,
        }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with path.open(mode, encoding="utf-8") as fh:
            fh.write(content)
    except Exception as exc:
        return {"ok": False, "error": f"escritura_fallo: {exc}", "path": rel_path}
    return {
        "ok": True,
        "path": rel_path,
        "bytes_written": len(content.encode("utf-8")),
        "mode": "append" if append else "write",
    }


def list_workspace_contents(rel_path: str = "", depth: int = 1) -> Dict[str, Any]:
    """Lista archivos/carpetas del sandbox (sin recorrer fuera de él)."""
    try:
        base = _safe_path(rel_path) if rel_path else WORKSPACE_ROOT
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "path": rel_path}
    if not base.exists():
        return {"ok": False, "error": "ruta_no_encontrada", "path": rel_path}
    if not base.is_dir():
        return {"ok": False, "error": "no_es_directorio", "path": rel_path}
    depth = max(1, min(int(depth or 1), 3))
    items: List[Dict[str, Any]] = []
    try:
        for entry in sorted(base.iterdir(), key=lambda e: (e.is_file(), e.name.lower())):
            try:
                entry.relative_to(WORKSPACE_ROOT)
            except ValueError:
                continue
            items.append(
                {
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size": entry.stat().st_size if entry.is_file() else 0,
                }
            )
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": f"listado_fallo: {exc}", "path": rel_path}
    return {
        "ok": True,
        "path": rel_path or ".",
        "root": str(WORKSPACE_ROOT),
        "count": len(items),
        "items": items[:200],
    }


# Esquema de herramientas para Tool Calling nativo de Gemini.
GEMINI_TOOL_DECLARATIONS = [
    {
        "name": "read_workspace_file",
        "description": (
            "Lee el contenido de un archivo dentro del workspace local de AURA "
            "(sandbox del repositorio). Usa para analizar scripts, codigo o "
            "documentos que el usuario mencione. Devuelve el texto del archivo."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Ruta relativa al workspace, ej: AME/recon.py",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "list_workspace_contents",
        "description": (
            "Lista archivos y carpetas dentro del workspace local de AURA. "
            "Usa para explorar la estructura del proyecto antes de leer o escribir."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Ruta relativa (opcional). Vacia = raiz del workspace.",
                },
                "depth": {
                    "type": "integer",
                    "description": "Profundidad de listado (1-3).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "write_workspace_file",
        "description": (
            "Escribe o anexa contenido a un archivo dentro del workspace local de "
            "AURA. Solo extensiones de texto permitidas. Usa para crear o modificar "
            "codigo estructurado cuando el usuario lo pida."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Ruta relativa al workspace, ej: AME/notas.md",
                },
                "content": {
                    "type": "string",
                    "description": "Contenido de texto a escribir.",
                },
                "append": {
                    "type": "boolean",
                    "description": "True para anexar en lugar de sobrescribir.",
                },
            },
            "required": ["path", "content"],
        },
    },
]


def dispatch_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta una herramienta de workspace por nombre (usado por tool calling)."""
    if name == "read_workspace_file":
        return read_workspace_file(args.get("path", ""))
    if name == "list_workspace_contents":
        return list_workspace_contents(args.get("path", ""), args.get("depth", 1))
    if name == "write_workspace_file":
        return write_workspace_file(
            args.get("path", ""), args.get("content", ""), bool(args.get("append", False))
        )
    return {"ok": False, "error": f"herramienta_desconocida: {name}"}
