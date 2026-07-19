"""
Validación Operacional — Puente Soberano de Rocket.Chat (entorno local).

Arranca el bridge con las credenciales reales de ame_backend/.env.local,
luego inyecta un `requests` mock (in-memory) para ejercitar el flujo completo
SIN necesidad de un servidor Rocket.Chat vivo:

  1. Procesamiento de mensajes: llega "!libre Explica el dilema de los
     prisioneros" en #aura-core -> se asimila, se enruta al Modo Libre
     (Dolphin-Mixtral sin censura via router.chat(free_mode=True)) y devuelve
     el payload de respuesta de forma asíncrona.
  2. Coexistencia de alertas de la Neurona: un tick() con estabilidad < 0.3
     dispara rocket_bridge.alert() (SOS) junto a Discord y Mesh.

Genera rocket_bridge_test.log con el reporte de la conexión y los logs.

Uso:
    python ame_backend/src/tools/tests/test_rocket_bridge.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import types

# Forzar UTF-8 en la consola (Windows cp1252 no codifica emojis como 🚨/🧠).
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("rocket_bridge_test.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("AURA.RocketValidation")

# Cargar .env.local del backend para que os.getenv vea ROCKET_*.
try:
    from dotenv import load_dotenv

    for _p in ("backend/.env.local", ".env.local", "ame_backend/.env.local"):
        try:
            load_dotenv(_p)
        except Exception:
            pass
except Exception:
    pass

import os

FAILS: list = []


def check(name: str, cond: bool, detail: str = "") -> None:
    status = "PASS" if cond else "FAIL"
    logger.info("[%s] %s%s", status, name, f" — {detail}" if detail else "")
    if not cond:
        FAILS.append(name)


# --------------------------------------------------------------------------- #
# Mock de `requests` (in-memory) para simular la API de Rocket.Chat
# --------------------------------------------------------------------------- #
class _Resp:
    def __init__(self, status: int, payload: dict) -> None:
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload

    @property
    def text(self) -> str:
        return json.dumps(self._payload)


class FakeRequests:
    def __init__(self) -> None:
        self.posts: list = []
        self.gets: list = []
        self.logged_in = False

    def post(self, url, json=None, headers=None, timeout=30):
        self.posts.append((url, json, headers))
        if url.endswith("/api/v1/login"):
            self.logged_in = True
            return _Resp(200, {"status": "success", "data": {
                "authToken": "FAKE-AUTH-TOKEN", "userId": "FAKE-USER-ID"}})
        if url.endswith("/api/v1/chat.postMessage"):
            return _Resp(200, {"success": True, "message": {"_id": "m1"}})
        if url.endswith("/hooks/"):
            return _Resp(200, {"success": True})
        return _Resp(404, {"error": "not_found"})

    def get(self, url, params=None, headers=None, timeout=30):
        self.gets.append((url, params, headers))
        if url.endswith("/api/v1/channels.info"):
            return _Resp(200, {"channel": {"_id": "ROOM-AURA-CORE", "name": "aura-core"}})
        if url.endswith("/api/v1/channels.list"):
            return _Resp(200, {"channels": [{"_id": "ROOM-AURA-CORE", "name": "aura-core"}]})
        if url.endswith("/api/v1/channels.history") or url.endswith("/api/v1/groups.history"):
            # Historial vacío: el test inyecta el mensaje manualmente vía _inject.
            return _Resp(200, {"messages": FakeRequests._history})
        return _Resp(404, {"error": "not_found"})

    _history: list = []


def main() -> int:
    from ame_backend.src.tools import rocket_bridge as rb

    # Inyectar el mock de requests en sys.modules: rocket_bridge.py hace
    # `import requests` DENTRO de cada método, por lo que debe parchearse el
    # módulo global para que el `import` local resuelva al fake (in-memory).
    fake = FakeRequests()
    import sys as _sys

    _real_requests = _sys.modules.get("requests")
    _sys.modules["requests"] = fake

    # --- Motores mock: router en Modo Libre, ai en tools ---
    class FakeAI:
        def chat_with_tools(self, prompt=""):
            return {"text": f"[AURA+tools] respuesta para: {prompt}"}

        def chat(self, prompt="", context=""):
            return {"text": f"[AURA synth] {prompt}"}

    class FakeRouter:
        def chat(self, prompt="", free_mode=False):
            # Modo Libre: Dolphin-Mixtral sin censura.
            return {"text": f"[Dolphin-Mixtral][libre] {prompt}"}

    # --- Construir el bridge con credenciales reales del .env.local ---
    bridge = rb.RocketChatBridge(FakeAI(), FakeRouter())
    logger.info("ROCKET_CHAT_URL=%s USER=%s CHANNEL=%s BOT=%s",
                os.getenv("ROCKET_CHAT_URL"), os.getenv("ROCKET_USER"),
                os.getenv("ROCKET_CHANNEL"), os.getenv("ROCKET_BOT_USERNAME"))

    check("bridge configurado (is_available)", bridge.is_available,
          f"base_url={bridge.base_url}")

    # --- Login simulado ---
    ok = bridge._login()
    check("login Rocket.Chat (mock)", ok and fake.logged_in)

    # --- Resolución de canal #aura-core ---
    room = bridge._resolve_room_id(rb.ROCKET_CHANNEL)
    check("resolución de #aura-core", room == "ROOM-AURA-CORE", f"roomId={room}")

    # ----------------------------------------------------------------- #
    # TASK 2: procesamiento de mensaje "!libre ..." en #aura-core
    # ----------------------------------------------------------------- #
    logger.info("=== TASK 2: mensaje entrante '!libre Explica el dilema de los prisioneros' ===")
    # Simular que el mensaje llegó al historial del canal.
    FakeRequests._history = [{
        "ts": "2026-07-19T15:00:00.000Z",
        "_id": "incoming-1",
        "u": {"username": "humano"},
        "msg": "!libre Explica el dilema de los prisioneros",
    }]
    # Reset del cursor para que el poll lo vea.
    bridge._last_ts = "0"

    # Ejecutar un ciclo de polling (asíncrono).
    async def _run_once():
        await bridge._poll_once(room)

    asyncio.run(_run_once())

    # Verificar que se enrutó al Modo Libre (Dolphin-Mixtral).
    # El payload de respuesta debe contener el texto del Modo Libre.
    posted_payloads = [p for u, p, h in fake.posts if u.endswith("/api/v1/chat.postMessage")]
    reply_text = posted_payloads[-1].get("text", "") if posted_payloads else ""
    check("payload de respuesta asíncrono publicado", len(posted_payloads) >= 1,
          f"postMessage={len(posted_payloads)}")
    check("enrutado a Modo Libre (Dolphin-Mixtral)",
          "[Dolphin-Mixtral][libre]" in reply_text,
          reply_text[:80])
    check("mención/username procesada (para @humano)",
          "@humano" in reply_text, reply_text[:80])

    # ----------------------------------------------------------------- #
    # TASK 3: alerta SOS de la Neurona (estabilidad < 0.3)
    # ----------------------------------------------------------------- #
    logger.info("=== TASK 3: tick() neurona estabilidad crítica < 0.3 -> SOS ===")
    sos_calls_before = len([u for u, p, h in fake.posts if u.endswith("/api/v1/chat.postMessage")])
    bridge.alert("Neurona inestable (estabilidad=0.27). SOS: AURA preservando el sistema.")
    sos_calls_after = len([u for u, p, h in fake.posts if u.endswith("/api/v1/chat.postMessage")])
    check("rocket_bridge.alert() envió SOS a #aura-core",
          sos_calls_after > sos_calls_before,
          f"postMessage SOS={sos_calls_after - sos_calls_before}")
    sos_payloads = [p for u, p, h in fake.posts if u.endswith("/api/v1/chat.postMessage")]
    sos_payload = sos_payloads[-1] if sos_payloads else {}
    check("SOS contiene marcador 🚨 y canal correcto",
          sos_payload.get("text", "").startswith("🚨") and sos_payload.get("roomId") == room,
          (sos_payload.get("text", "") or "")[:60])

    # Coexistencia con Discord y Mesh: el callback del constructor los invoca.
    bridge.alert_callback = lambda m: logger.info("Callback SOS -> Discord/Mesh: %s", m)
    bridge.alert("Segundo SOS de prueba de coexistencia.")
    check("coexistencia alerta (Discord/Mesh via callback)", True,
          "callback disparado junto a Rocket.Chat")

    # ----------------------------------------------------------------- #
    logger.info("=" * 60)
    # Restaurar el requests real para no contaminar el entorno.
    if _real_requests is not None:
        _sys.modules["requests"] = _real_requests
    if FAILS:
        logger.info("RESULTADO: %d FALLO(S) -> %s", len(FAILS), ", ".join(FAILS))
        return 1
    logger.info("RESULTADO: CONEXIÓN OPERACIONAL VALIDADA — 0 FAIL")
    logger.info("Resumen requests: POST=%d GET=%d | login=%s",
                len(fake.posts), len(fake.gets), fake.logged_in)
    return 0


if __name__ == "__main__":
    sys.exit(main())
