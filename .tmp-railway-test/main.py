"""AURA Backend main entrypoint."""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI

logger = logging.getLogger(__name__)

app = FastAPI(title="AURA Backend")


@app.get("/")
def root() -> Dict[str, Any]:
    return {"status": "ok", "service": "aura-backend"}


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}


@app.get("/api/status")
def api_status() -> Dict[str, Any]:
    return {
        "bots": [
            {"id": "bot-1", "name": "Roller Miner", "status": "Idle"},
            {"id": "bot-2", "name": "Survey Harvester", "status": "Stopped"},
            {"id": "bot-3", "name": "OSINT Recon", "status": "Stopped"},
        ]
    }


@app.get("/api/balance")
def api_balance() -> Dict[str, Any]:
    return {"total_balance": 0.0, "currency": "USD"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
