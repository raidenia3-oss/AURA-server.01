"""
Puente Táctico de Discord — Red de Comunicación Soberana.

Cliente asíncrono (discord.py) que conecta AURA a un canal privado de Discord.
Enruta los comandos del usuario al motor ``chat_with_tools`` (con herramientas
de workspace) o al "Modo Libre" sin censura, y emite alertas automáticas de la
Neurona Artificial cuando la estabilidad cae o hay keep-alive crítico.

Diseño resiliente: si discord.py no está instalado o falta DISCORD_TOKEN, el
módulo es un no-op que no bloquea el arranque de FastAPI. El bot corre en su
propio background task (asyncio), ajeno al bucle de telemetría de la neurona.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Prefijo de comandos en el canal privado.
CMD_PREFIX = os.getenv("DISCORD_CMD_PREFIX", "!aura")

# Clave del servidor de alertas (canal donde AURA avisa inestabilidad).
ALERT_CHANNEL_ID = os.getenv("DISCORD_ALERT_CHANNEL_ID")

# Señal para activar Modo Libre desde Discord.
FREE_TRIGGER = "!libre"


class DiscordBridge:
    """Orquesta el cliente de Discord y su integración con AURA."""

    def __init__(
        self,
        ai_engine: Any,
        router_engine: Any,
        alert_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.ai = ai_engine
        self.router = router_engine
        self.alert_callback = alert_callback
        self.token = os.getenv("DISCORD_TOKEN")
        self.client: Any = None
        self._task: Optional[asyncio.Task] = None
        self._available = self._check_available()

    def _check_available(self) -> bool:
        if not self.token:
            return False
        try:
            import discord  # noqa: F401
        except Exception:
            logger.warning(
                "discord.py no instalado; el Puente Táctico de Discord está inactivo."
            )
            return False
        return True

    @property
    def is_available(self) -> bool:
        return self._available

    def start(self) -> None:
        """Arranca el bot en un background task (no bloquea el event loop)."""
        if not self._available:
            return
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._run(), name="discord-bridge")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        if self.client is not None:
            try:
                await self.client.close()
            except Exception:
                pass

    async def _run(self) -> None:
        try:
            import discord
            from discord.ext import commands

            intents = discord.Intents.default()
            intents.message_content = True
            intents.guilds = True
            intents.dm_messages = True

            bot = commands.Bot(command_prefix=CMD_PREFIX, intents=intents)

            @bot.event
            async def on_ready() -> None:
                logger.info("Discord Bridge conectado como %s", bot.user)

            @bot.event
            async def on_message(msg: Any) -> None:
                # Ignorar los propios mensajes y los de otros bots.
                if msg.author == bot.user or msg.author.bot:
                    return
                text = msg.content or ""
                if not text.startswith(CMD_PREFIX) and not text.startswith("!"):
                    return
                # Quitar prefijo para obtener el prompt real.
                prompt = text
                for p in (CMD_PREFIX, "!"):
                    if prompt.startswith(p):
                        prompt = prompt[len(p):].strip()
                        break
                if not prompt:
                    return
                await self._handle(bot, msg, prompt)

            self.client = bot
            await bot.start(self.token)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Discord Bridge cayó: %s", exc)

    async def _handle(self, bot: Any, msg: Any, prompt: str) -> None:
        free_mode = prompt.startswith(FREE_TRIGGER)
        if free_mode:
            prompt = prompt[len(FREE_TRIGGER):].strip()
        try:
            if free_mode:
                res = self.router.chat(prompt=prompt, free_mode=True)
                reply = res.get("text") or res.get("error") or "(sin respuesta)"
                tag = "🔓 [Modo Libre]"
            else:
                res = self.ai.chat_with_tools(prompt=prompt)
                reply = res.get("text") or "(sin respuesta)"
                tag = "🧠 [AURA + tools]"
            chunks = [reply[i : i + 1900] for i in range(0, len(reply), 1900)] or [reply]
            for chunk in chunks[:4]:
                await msg.channel.send(f"{tag}\n{chunk}")
        except Exception as exc:
            logger.error("Discord handle falló: %s", exc)
            try:
                await msg.channel.send(f"⚠️ Error de AURA: {exc}")
            except Exception:
                pass

    def alert(self, message: str) -> None:
        """Envía una alerta de la Neurona a Discord (mejor-effort)."""
        if not self._available or self.client is None:
            return
        try:
            ch_id = ALERT_CHANNEL_ID or os.getenv("DISCORD_CHANNEL_ID")
            if not ch_id:
                return
            channel = self.client.get_channel(int(ch_id))
            if channel is not None:
                asyncio.create_task(channel.send(f"🚨 {message}"))
        except Exception as exc:
            logger.error("Discord alert falló: %s", exc)
        # Si hay callback alternativo (p.ej. log), también se invoca.
        if self.alert_callback:
            try:
                self.alert_callback(message)
            except Exception:
                pass
