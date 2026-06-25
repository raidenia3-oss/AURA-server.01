"""
AME Backend - Servidor principal.
"""

from __future__ import annotations

import base64
import io
import os
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import jwt
import psutil
from PIL import ImageGrab

from src.automation.stealth_browser import StealthBrowser
from src.services.ai_engine import AIEngine


class _Server:
    def __init__(self) -> None:
        self.app = FastAPI(title="AME Backend", version="0.1.0")
        self._secret = os.getenv("JWT_SECRET", "ame-secret-key-change-in-production")
        self.browser = StealthBrowser(headless=True)
        self.ai = AIEngine()
        self._register_routes()

    def _register_routes(self) -> None:
        app = self.app

        @app.get("/health")
        async def health() -> JSONResponse:
            return JSONResponse({"status": "ok", "ts": datetime.now(timezone.utc).isoformat()})

        @app.get("/ai/health")
        async def ai_health() -> JSONResponse:
            return JSONResponse(self.ai.health_check())

        @app.post("/auth/token")
        async def auth_token(user_id: str = "ame-user") -> JSONResponse:
            token = jwt.encode(
                {"sub": user_id, "iat": datetime.now(timezone.utc)}, self._secret, algorithm="HS256"
            )
            return JSONResponse({"token": token, "user_id": user_id})

        @app.websocket("/ws/bridge")
        async def ws_bridge(websocket: WebSocket) -> None:
            try:
                await websocket.accept()
                first = await websocket.receive_text()
                try:
                    jwt.decode(first, self._secret, algorithms=["HS256"])
                except Exception:
                    await websocket.close(code=1008)
                    return
                await websocket.send_text("connected")
                while True:
                    try:
                        msg = await asyncio.wait_for(websocket.receive_text(), timeout=10)
                        if msg.lower() == "ping":
                            await websocket.send_json(
                                {"ping": datetime.now(timezone.utc).isoformat()}
                            )
                            continue
                        await websocket.send_text(f"ACK:{msg[:64]}")
                    except asyncio.TimeoutError:
                        await websocket.send_json({"ping": datetime.now(timezone.utc).isoformat()})
            except WebSocketDisconnect:
                pass
            except Exception:
                try:
                    await websocket.close()
                except Exception:
                    pass

        @app.websocket("/ws/browser-stream")
        async def ws_browser_stream(websocket: WebSocket) -> None:
            await websocket.accept()
            try:
                await websocket.send_json({"status": "connected", "engine": "screen"})
                while True:
                    try:
                        frame = await self._capture_screen()
                        if frame:
                            await websocket.send_bytes(frame)
                        else:
                            await websocket.send_json({"status": "waiting"})
                    except Exception as exc:
                        await websocket.send_json({"status": "error", "detail": str(exc)})
                        break
            except WebSocketDisconnect:
                pass
            finally:
                try:
                    await websocket.close()
                except Exception:
                    pass

    async def _capture_screen(self) -> Optional[bytes]:
        try:
            screenshot = ImageGrab.grab()
            buffer = io.BytesIO()
            screenshot.save(buffer, format="JPEG", quality=55)
            return buffer.getvalue()
        except Exception:
            return None


def create_app() -> FastAPI:
    s = _Server()
    return s.app


app = create_app()
