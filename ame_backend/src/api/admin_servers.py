"""FastAPI router for multi-server admin management.

Exposes the ServerManager over HTTP:
- GET  /api/admin/servers            -> list servers + active target
- POST /api/admin/servers            -> action=register|switch|deploy
- PUT  /api/admin/servers            -> sync DATABASE_URL to all registered
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Request

from ame_backend.src.deployment.server_adapter import ServerType, manager

router = APIRouter(prefix="/api/admin/servers", tags=["admin"])


@router.get("")
async def list_servers() -> Dict[str, Any]:
    return manager.list_servers()


@router.post("")
async def servers_action(request: Request) -> Dict[str, Any]:
    try:
        body: Dict[str, Any] = await request.json()
    except Exception:
        return {"ok": False, "error": "JSON invalido"}

    action = body.get("action")
    raw_type = body.get("server_type")

    if action in {"register", "switch", "deploy"} and not raw_type:
        return {"ok": False, "error": "Falta 'server_type'"}

    server_type = None
    if raw_type:
        try:
            server_type = ServerType(raw_type)
        except ValueError:
            return {"ok": False, "error": f"server_type invalido: {raw_type}"}

    if action == "register":
        ok = manager.register_server(server_type, body.get("credentials", {}))
        return {"ok": ok, "registered": ok, "server_type": server_type.value}

    if action == "switch":
        return manager.switch_server(server_type)

    if action == "deploy":
        return manager.deploy_to(server_type, body.get("code_path", "."))

    return {"ok": False, "error": f"accion desconocida: {action}"}


@router.put("")
async def sync_database(request: Request) -> Dict[str, Any]:
    try:
        body: Dict[str, Any] = await request.json()
    except Exception:
        return {"ok": False, "error": "JSON invalido"}
    db_url = body.get("db_url")
    if not db_url:
        return {"ok": False, "error": "Falta 'db_url'"}
    return manager.sync_all(db_url)
