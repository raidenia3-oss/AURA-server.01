"""
Puente Soberano de Rocket.Chat — Interfaz de Comunicación Definitiva de AURA.

Conector asíncrono que integra AURA con un servidor Rocket.Chat usando sus
APIs REST nativas (login por usuario/contraseña o token de Webhook) e
Incoming/Outgoing Webhooks. Permite:

  * Escuchar un canal táctico (ej. #aura-core) vía polling del endpoint
    ``channels.history``/``groups.history`` y responder cuando AURA es
    mencionada o se usan comandos con prefijo.
  * Enrutar esos mensajes al motor ``chat_with_tools`` (con herramientas de
    workspace) o al "Modo Libre" sin censura (Dolphin-Mixtral) a través del
    enrutador multi-modelo.
  * Publicar alertas prioritarias de la Neurona Artificial cuando la
    estabilidad cae por debajo del umbral (además de Discord y la Mesh).

Diseño resiliente: si faltan las variables ``ROCKET_CHAT_URL`` /
``ROCKET_USER``+``ROCKET_PASSWORD`` (o ``ROCKET_WEBHOOK_URL``), el módulo es
un NO-OP que no bloquea el arranque de FastAPI. El listener corre en su propio
background task (asyncio), ajeno al bucle de telemetría de la neurona.
"""

from __future__ import annotations

import asyncio
import functools
import logging
import os
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Canal táctico donde AURA opera (sin el '#' inicial en la config).
ROCKET_CHANNEL = os.getenv("ROCKET_CHANNEL", "aura-core")

# Prefijo de comandos en el canal.
CMD_PREFIX = os.getenv("ROCKET_CMD_PREFIX", "!aura")

# Señal para activar el Modo Libre desde Rocket.Chat.
FREE_TRIGGER = "!libre"

# Intervalo de polling del histórico del canal (segundos).
_POLL_INTERVAL = float(os.getenv("ROCKET_POLL_INTERVAL", "5.0"))

# Tamaño máximo de mensaje por chunk (límite保守 de Rocket.Chat).
_MAX_MSG_LEN = 1800


class RocketChatBridge:
    """Orquesta el conector asíncrono a Rocket.Chat (REST + Webhooks)."""

    def __init__(
        self,
        ai_engine: Any,
        router_engine: Any,
        alert_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.ai = ai_engine
        self.router = router_engine
        self.alert_callback = alert_callback

        self.base_url = (os.getenv("ROCKET_CHAT_URL") or "").rstrip("/")
        self.user = os.getenv("ROCKET_USER")
        self.password = os.getenv("ROCKET_PASSWORD")
        self.webhook_url = os.getenv("ROCKET_WEBHOOK_URL")
        self.bot_username = os.getenv("ROCKET_BOT_USERNAME", "aura")

        self._auth_token: Optional[str] = None
        self._user_id: Optional[str] = None
        self._task: Optional[asyncio.Task] = None
        self._last_ts: str = "0"
        # [PARCHE AUTO-AUDITORÍA] Lock para proteger el estado de credenciales
        # (authToken/userId) que se muta en _login (task del bridge) y se lee en
        # _post/_get/send_message/alert (también invocados desde el monitor de
        # la neurona). Sin esto hay una condición de carrera de estado mutable.
        self._cred_lock = asyncio.Lock()
        # Flag de conexión de producción (enlazado al login real).
        self._connected = False
        self._available = self._check_available()

    @property
    def is_connected(self) -> bool:
        """True tras un login exitoso con auth token real de Rocket.Chat."""
        return self._connected

    # ------------------------------------------------------------------ #
    # Disponibilidad / resiliencia (no-op si no está configurado)
    # ------------------------------------------------------------------ #
    def _check_available(self) -> bool:
        if not self.base_url:
            logger.info(
                "ROCKET_CHAT_URL no configurado; el Puente de Rocket.Chat es no-op."
            )
            return False
        # Necesita login por usuario/contraseña, o un webhook de salida.
        has_login = bool(self.user and self.password)
        has_webhook = bool(self.webhook_url)
        if not (has_login or has_webhook):
            logger.warning(
                "Rocket.Chat: falta ROCKET_USER/ROCKET_PASSWORD o "
                "ROCKET_WEBHOOK_URL; el puente queda inactivo (no-op)."
            )
            return False
        return True

    @property
    def is_available(self) -> bool:
        return self._available

    # ------------------------------------------------------------------ #
    # Cliente HTTP asíncrono (sin bloquear el event loop)
    # ------------------------------------------------------------------ #
    # [PARCHE AUTO-AUDITORÍA] Las llamadas requests son BLOQUEANTES. Ejecutarlas
    # dentro del event loop de FastAPI congela todo AURA (cuello de botella
    # asíncrono). Se delegan a un thread del executor vía run_in_executor,
    # manteniendo el loop libre para la Neurona y la Mesh.
    async def _areq(self, method: str, url: str, **kwargs: Any) -> Optional[dict]:
        """Envía una petición HTTP en un executor y devuelve el JSON o None."""
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(
                None,
                functools.partial(self._sync_req, method, url, **kwargs),
            )
        except Exception as exc:  # pragma: no cover - resiliencia
            logger.error("Rocket.Chat %s falló (%s): %s", method, url, exc)
            return None

    def _sync_req(self, method: str, url: str, **kwargs: Any) -> Optional[dict]:
        import requests

        resp = requests.request(method, url, timeout=kwargs.pop("timeout", 30), **kwargs)
        if resp.status_code >= 400:
            logger.error(
                "Rocket.Chat %s %s -> %s: %s",
                method, url, resp.status_code, resp.text[:200],
            )
            return None
        try:
            return resp.json()
        except Exception:
            return None

    # ------------------------------------------------------------------ #
    # Ciclo de vida
    # ------------------------------------------------------------------ #
    def start(self) -> None:
        if not self._available:
            return
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(), name="rocket-bridge")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None

    # ------------------------------------------------------------------ #
    # Cliente HTTP (requests, ya en requirements)
    # ------------------------------------------------------------------ #
    # [PARCHE AUTO-AUDITORÍA] _post/_get son SÍNCRONOS (se usan desde
    # send_message/alert, invocados desde el monitor de la neurona). Las
    # variantes _apost/_aget son ASÍNCRONAS y corren en un executor para no
    # bloquear el event loop del bridge.
    def _headers(self, auth: bool = True) -> dict:
        h = {"Content-Type": "application/json"}
        if auth and self._auth_token and self._user_id:
            h["X-Auth-Token"] = self._auth_token
            h["X-User-Id"] = self._user_id
        return h

    def _post(self, path: str, json: dict, auth: bool = True) -> Optional[dict]:
        if not self._available:
            return None
        return self._sync_req(
            "POST", f"{self.base_url}{path}", json=json, headers=self._headers(auth)
        )

    def _get(self, path: str, params: Optional[dict] = None) -> Optional[dict]:
        if not self._available:
            return None
        return self._sync_req(
            "GET", f"{self.base_url}{path}", params=params or {}, headers=self._headers(True)
        )

    async def _apost(self, path: str, json: dict, auth: bool = True) -> Optional[dict]:
        if not self._available:
            return None
        return await self._areq(
            "POST", f"{self.base_url}{path}", json=json, headers=self._headers(auth)
        )

    async def _aget(self, path: str, params: Optional[dict] = None) -> Optional[dict]:
        if not self._available:
            return None
        return await self._areq(
            "GET", f"{self.base_url}{path}", params=params or {}, headers=self._headers(True)
        )

    # ------------------------------------------------------------------ #
    # Autenticación REST
    # ------------------------------------------------------------------ #
    async def _login(self) -> bool:
        if not (self.user and self.password):
            # Modo solo-webhook: no requiere login de usuario.
            return bool(self.webhook_url)
        # [PARCHE AUTO-AUDITORÍA] El lock serializa la mutación de credenciales
        # frente a lecturas concurrentes desde send_message/alert (monitor).
        async with self._cred_lock:
            res = await self._apost(
                "/api/v1/login",
                {"user": self.user, "password": self.password},
                auth=False,
            )
            if not res or not res.get("data", {}).get("authToken"):
                status = (res or {}).get("status") or "sin_respuesta"
                logger.error(
                    "Rocket.Chat login FALLÓ para '%s' (status=%s). El puente "
                    "quedará inactivo hasta reintentar en el próximo ciclo.",
                    self.user, status,
                )
                self._connected = False
                return False
            self._auth_token = res["data"]["authToken"]
            self._user_id = res["data"]["userId"]
            self._connected = True
        # Log de producción detallado: confirma la recepción del auth token real
        # (enmascarado) para saber que el enlace con Rocket.Chat está vivo.
        token_mask = (self._auth_token[:6] + "…" + self._auth_token[-4:]) \
            if self._auth_token and len(self._auth_token) > 10 else "***"
        logger.info(
            "✅ Rocket.Chat ENLACE DE PRODUCCIÓN establecido: autenticado como "
            "'%s' (userId=%s, authToken=%s). Servidor: %s",
            self.user, self._user_id, token_mask, self.base_url,
        )
        return True

    async def _resolve_room_id(self, channel: str) -> Optional[str]:
        """Resuelve el roomId de #canal (o nombre directo) para el polling."""
        # Intenta canal público.
        res = await self._aget(
            "/api/v1/channels.info", params={"roomName": channel.lstrip("#")}
        )
        if res and res.get("channel", {}).get("_id"):
            return res["channel"]["_id"]
        # Intenta grupo privado.
        res = await self._aget(
            "/api/v1/groups.info", params={"roomName": channel.lstrip("#")}
        )
        if res and res.get("group", {}).get("_id"):
            return res["group"]["_id"]
        # Fallback: listar canales y buscar coincidencia.
        res = await self._aget("/api/v1/channels.list", params={"count": 200})
        for ch in (res or {}).get("channels", []):
            if ch.get("name") == channel.lstrip("#"):
                return ch.get("_id")
        logger.warning("Rocket.Chat: no se encontró el canal #%s", channel)
        return None

    # ------------------------------------------------------------------ #
    # Envío de mensajes
    # ------------------------------------------------------------------ #
    def _resolve_room_id_sync(self, channel: str) -> Optional[str]:
        """Versión SÍNCRONA para send_message/alert (contexto sin await)."""
        res = self._get(
            "/api/v1/channels.info", params={"roomName": channel.lstrip("#")}
        )
        if res and res.get("channel", {}).get("_id"):
            return res["channel"]["_id"]
        res = self._get(
            "/api/v1/groups.info", params={"roomName": channel.lstrip("#")}
        )
        if res and res.get("group", {}).get("_id"):
            return res["group"]["_id"]
        res = self._get("/api/v1/channels.list", params={"count": 200})
        for ch in (res or {}).get("channels", []):
            if ch.get("name") == channel.lstrip("#"):
                return ch.get("_id")
        return None

    def send_message(self, text: str, channel: Optional[str] = None) -> bool:
        """Publica un mensaje vía API REST o Incoming Webhook.

        Prioriza el webhook de salida (ROCKET_WEBHOOK_URL) si está definido;
        si no, usa la API REST autenticada. Es no-op si no está disponible.
        """
        if not self._available:
            return False
        target = channel or ROCKET_CHANNEL
        # 1) Incoming Webhook (más simple, no requiere auth de usuario).
        if self.webhook_url:
            try:
                import requests

                payload = {
                    "text": text,
                    "username": self.bot_username,
                    "channel": f"#{target.lstrip('#')}",
                }
                resp = requests.post(self.webhook_url, json=payload, timeout=30)
                if resp.status_code < 400:
                    return True
            except Exception as exc:  # pragma: no cover
                logger.error("Rocket.Chat webhook falló: %s", exc)
            # Si hay login, reintenta por REST; si no, sale.
            if not (self._auth_token and self._user_id):
                return False
        # 2) API REST autenticada.
        room_id = self._resolve_room_id_sync(target)
        if not room_id:
            return False
        res = self._post(
            "/api/v1/chat.postMessage",
            {"roomId": room_id, "text": text},
        )
        return bool(res and res.get("success"))

    def alert(self, message: str) -> None:
        """Alerta prioritaria de la Neurona Artificial a Rocket.Chat."""
        if not self._available:
            return
        ok = self.send_message(f"🚨 {message}")
        if ok:
            logger.info("Alerta de neurona enviada a Rocket.Chat (#%s).", ROCKET_CHANNEL)
        if self.alert_callback:
            try:
                self.alert_callback(message)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Loop principal: polling del canal + enrutado de mensajes
    # ------------------------------------------------------------------ #
    def _mentioned(self, text: str) -> bool:
        """Detecta si AURA fue mencionada o se usó el prefijo de comando."""
        low = (text or "").lower()
        return (
            self.bot_username.lower() in low
            or CMD_PREFIX.lower() in low
            or low.startswith("!")
        )

    async def _run(self) -> None:
        try:
            if not await self._login():
                logger.warning("Rocket.Chat bridge inactivo: sin autenticación.")
                return
            room_id = await self._resolve_room_id(ROCKET_CHANNEL)
            if not room_id:
                logger.warning("Rocket.Chat bridge detenido: canal no resoluble.")
                return
            logger.info(
                "Rocket.Chat Bridge escuchando #%s (polling %ss).",
                ROCKET_CHANNEL,
                _POLL_INTERVAL,
            )
            while True:
                await self._poll_once(room_id)
                await asyncio.sleep(_POLL_INTERVAL)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - resiliencia
            logger.error("Rocket.Chat Bridge cayó: %s", exc)

    async def _poll_once(self, room_id: str) -> None:
        # [PARCHE AUTO-AUDITORÍA] I/O asíncrono vía executor: no bloquea el loop.
        res = await self._aget(
            "/api/v1/channels.history",
            params={"roomId": room_id, "count": 20},
        )
        if not res:
            # Reintenta como grupo privado.
            res = await self._aget(
                "/api/v1/groups.history", params={"roomId": room_id, "count": 20}
            )
        if not res:
            return
        messages = (res.get("messages") or [])[::-1]  # más antiguos primero
        for msg in messages:
            ts = msg.get("ts") or msg.get("_id") or ""
            if ts <= self._last_ts:
                continue
            self._last_ts = ts
            text = msg.get("msg") or ""
            user = (msg.get("u") or {}).get("username") or "unknown"
            if user == self.bot_username:
                continue  # ignorar los propios mensajes
            if not self._mentioned(text):
                continue
            prompt = self._strip_prefix(text)
            if not prompt:
                continue
            await self._handle(prompt, user)

    def _strip_prefix(self, text: str) -> str:
        """Quita la mención al bot y el prefijo de comando, conservando
        disparadores especiales como '!libre' para que _handle los detecte."""
        t = text.strip()
        # 1) Mención explícita al bot (ej. "@aura.bot").
        mention = f"@{self.bot_username.lower()}"
        if t.lower().startswith(mention):
            t = t[len(mention):].strip()
        # 2) Prefijo de comando (!aura), salvo que sea un disparador libre.
        if t.lower().startswith(CMD_PREFIX.lower()) and not t.lower().startswith(
            FREE_TRIGGER.lower()
        ):
            t = t[len(CMD_PREFIX):].strip()
        return t

    async def _handle(self, prompt: str, user: str) -> None:
        free_mode = prompt.lower().startswith(FREE_TRIGGER.lower())
        if free_mode:
            # Quitar el disparador '!libre' (insensible a mayúsculas).
            for trig in (FREE_TRIGGER, FREE_TRIGGER.lower()):
                if prompt.lower().startswith(trig.lower()):
                    prompt = prompt[len(trig):].strip()
                    break
        try:
            if free_mode:
                res = self.router.chat(prompt=prompt, free_mode=True)
                reply = res.get("text") or res.get("error") or "(sin respuesta)"
                tag = "🔓 [Modo Libre]"
            else:
                res = self.ai.chat_with_tools(prompt=prompt)
                reply = res.get("text") or "(sin respuesta)"
                tag = "🧠 [AURA + tools]"
            body = f"{tag} (para @{user})\n{reply}"
            chunks = [
                body[i : i + _MAX_MSG_LEN]
                for i in range(0, len(body), _MAX_MSG_LEN)
            ] or [body]
            for chunk in chunks[:4]:
                self.send_message(chunk)
        except Exception as exc:
            logger.error("Rocket.Chat handle falló: %s", exc)
            try:
                self.send_message(f"⚠️ Error de AURA: {exc}")
            except Exception:
                pass
