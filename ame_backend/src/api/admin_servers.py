"""FastAPI router for multi-server admin management with JWT auth + RBAC + audit.

Exposes the ServerManager over HTTP:
- GET  /api/admin/servers            -> list servers + active target   (servers:read)
- POST /api/admin/servers            -> action=register|switch|deploy  (servers:write / servers:switch)
- PUT  /api/admin/servers            -> sync DATABASE_URL to all       (servers:sync)
- GET  /api/admin/servers/audit-logs -> read audit log                 (audit:read)
- POST /api/admin/servers/generate-token -> mint token (admin only)
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from ame_backend.src.deployment.server_adapter import ServerType, manager
from ame_backend.src.lib.auth import (
    ROLE_PERMISSIONS,
    Role,
    audit_logger,
    auth_manager,
    get_current_user,
    rate_limiter,
)

router = APIRouter(prefix="/api/admin/servers", tags=["admin"])


def _check_rate(current_user: Dict) -> None:
    if not rate_limiter.is_allowed(current_user.get("user_id")):
        raise HTTPException(status_code=429, detail="Rate limit exceeded (10 req/60s)")


def _permitted(current_user: Dict, permission: str) -> None:
    role = Role(current_user.get("role"))
    if permission not in ROLE_PERMISSIONS.get(role, []):
        audit_logger.log_action(
            current_user.get("user_id"),
            permission,
            "servers",
            status="denied",
        )
        raise HTTPException(status_code=403, detail="Permission denied")


@router.get("")
async def list_servers(current_user: Dict = Depends(get_current_user)) -> Dict[str, Any]:
    _check_rate(current_user)
    _permitted(current_user, "servers:read")
    audit_logger.log_action(current_user.get("user_id"), "LIST_SERVERS", "servers")
    return manager.list_servers()


@router.post("")
async def servers_action(
    request: Request, current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    _check_rate(current_user)
    try:
        body: Dict[str, Any] = await request.json()
    except Exception:
        return {"ok": False, "error": "JSON invalido"}

    action = body.get("action")
    raw_type = body.get("server_type")
    user_id = current_user.get("user_id")

    if action in {"register", "switch", "deploy"} and not raw_type:
        return {"ok": False, "error": "Falta 'server_type'"}

    server_type: Optional[ServerType] = None
    if raw_type:
        try:
            server_type = ServerType(raw_type)
        except ValueError:
            audit_logger.log_action(
                user_id, "ACTION", raw_type,
                details={"action": action, "error": "invalid_type"}, status="failed",
            )
            return {"ok": False, "error": f"server_type invalido: {raw_type}"}

    if action == "register":
        _permitted(current_user, "servers:write")
        ok = manager.register_server(server_type, body.get("credentials", {}))
        audit_logger.log_action(
            user_id, "REGISTER_SERVER", server_type.value,
            details={"ok": ok},
            status="success" if ok else "failed",
        )
        return {"ok": ok, "registered": ok, "server_type": server_type.value}

    if action == "switch":
        _permitted(current_user, "servers:switch")
        result = manager.switch_server(server_type)
        audit_logger.log_action(
            user_id, "SWITCH_SERVER", server_type.value,
            details=result, status="success" if result.get("ok") else "failed",
        )
        return result

    if action == "deploy":
        _permitted(current_user, "servers:write")
        result = manager.deploy_to(server_type, body.get("code_path", "."))
        audit_logger.log_action(
            user_id, "DEPLOY_SERVER", server_type.value,
            details=result, status="success" if result.get("ok") else "failed",
        )
        return result

    audit_logger.log_action(
        user_id, "ACTION", "servers",
        details={"action": action, "error": "unknown_action"}, status="failed",
    )
    return {"ok": False, "error": f"accion desconocida: {action}"}


@router.put("")
async def sync_database(
    request: Request, current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    _check_rate(current_user)
    _permitted(current_user, "servers:sync")
    user_id = current_user.get("user_id")
    try:
        body: Dict[str, Any] = await request.json()
    except Exception:
        return {"ok": False, "error": "JSON invalido"}
    db_url = body.get("db_url")
    if not db_url:
        return {"ok": False, "error": "Falta 'db_url'"}
    result = manager.sync_all(db_url)
    audit_logger.log_action(user_id, "SYNC_DATABASES", "databases", details=result)
    return result


@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = 50, current_user: Dict = Depends(get_current_user)
) -> Dict[str, Any]:
    _permitted(current_user, "audit:read")
    return {"logs": audit_logger.read_logs(limit=limit)}


@router.post("/generate-token")
async def generate_token(
    request: Request, current_user: Dict = Depends(get_current_user)
) -> Dict[str, str]:
    user_id = current_user.get("user_id")
    role = Role(current_user.get("role"))
    if role != Role.ADMIN:
        audit_logger.log_action(user_id, "GENERATE_TOKEN", "token", status="denied")
        raise HTTPException(status_code=403, detail="Only admins can generate tokens")
    try:
        body: Dict[str, Any] = await request.json()
    except Exception:
        body = {}
    target_user = body.get("user_id", user_id)
    try:
        target_role = Role(body.get("role", "viewer"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid role")
    token = auth_manager.create_token(target_user, target_role)
    audit_logger.log_action(
        user_id, "GENERATE_TOKEN", target_user,
        details={"target_user": target_user, "target_role": target_role.value},
    )
    return {
        "token": token,
        "user_id": target_user,
        "role": target_role.value,
        "expires_in": "24 hours",
    }
