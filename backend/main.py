"""AURA News API - FastAPI app for the autonomous news worker.

Serves health and news-recommendation endpoints consumed by
``news_worker.py`` and the integration/N8N layer, and (optionally) runs the
news worker loop in a background thread so a single deployment provides
both the API and the scheduled fetching.

Run with:  uvicorn backend.main:app --host 0.0.0.0 --port $PORT
"""
from __future__ import annotations

import os
import logging
import threading
from typing import Any, Dict, List

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("AURANewsAPI")

app = FastAPI(title="AURA News API", version="1.0.0")

_latest_recommendations: List[Dict[str, Any]] = []


@app.get("/api/health")
@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "healthy", "service": "aura-news-api"}


@app.post("/api/news/recommend")
async def receive_recommendations(request: Request) -> JSONResponse:
    global _latest_recommendations
    try:
        payload: Any = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "invalid JSON"})

    articles = payload.get("articles", []) if isinstance(payload, dict) else []
    _latest_recommendations = articles
    logger.info("Recibidas %d recomendaciones de noticias", len(articles))
    return JSONResponse(content={"status": "ok", "count": len(articles)})


@app.get("/api/news/recommend")
async def get_recommendations() -> Dict[str, Any]:
    return {"articles": _latest_recommendations}


def _start_worker() -> None:
    """Launch news_worker.run_worker() in a daemon thread if configured."""
    if not os.getenv("DATABASE_URL"):
        logger.warning("DATABASE_URL no configurada: el worker de noticias no arrancara.")
        return
    try:
        import news_worker  # sibling module

        thread = threading.Thread(target=news_worker.run_worker, daemon=True)
        thread.start()
        logger.info("Worker de noticias iniciado en segundo plano.")
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("No se pudo iniciar el worker de noticias: %s", exc)


@app.on_event("startup")
async def _on_startup() -> None:
    _start_worker()


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )
