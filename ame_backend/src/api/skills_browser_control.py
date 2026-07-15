"""FastAPI router exposing the browser-control skill to AURA/AME."""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Request

from ame_backend.src.automation.browser_control import BrowserControl

router = APIRouter(prefix="/api/skills/browser-control", tags=["skills"])

SKILL_DESCRIPTOR = {
    "id": "browser_control",
    "name": "Control de Navegador",
    "description": (
        "Permite a AURA/AME controlar un navegador (navegar, extraer texto, "
        "clic, rellenar, ejecutar JS, capturar). Requiere Playwright."
    ),
    "actions": ["navigate", "extract_text", "click", "fill", "evaluate", "screenshot"],
    "available": BrowserControl.available(),
}


@router.get("")
async def describe() -> Dict[str, Any]:
    return {"skill": SKILL_DESCRIPTOR}


@router.post("")
async def execute(request: Request) -> Dict[str, Any]:
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception:
        return {"ok": False, "error": "JSON invalido"}

    action = payload.get("action")
    if not action:
        return {"ok": False, "error": "Falta 'action'"}

    return await BrowserControl().run(action, payload.get("payload", {}))
