import os
import logging

import requests
import discord
from discord.ext import commands

TARGET_CHAT_URL = os.getenv("AURA_CHAT_URL", "https://aura-server-01.vercel.app/chat")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)


def build_payload(message: discord.Message) -> dict:
    channel_name = getattr(message.channel, "name", str(message.channel))
    return {
        "message": message.content,
        "user": str(message.author),
        "channel": f"{message.guild.name if message.guild else 'DM'} / {channel_name}",
        "channel_id": str(message.channel.id),
        "guild_id": str(message.guild.id) if message.guild else None,
    }


@bot.event
async def on_ready():
    logging.info("✅ AURA Discord bot conectado como %s", bot.user)
    logging.info("🌐 Enviando mensajes a %s", TARGET_CHAT_URL)


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    text = message.content.strip()
    if not text:
        return

    payload = build_payload(message)
    logging.info("📨 Enviando mensaje de Discord a AURA: %s", payload)

    try:
        response = requests.post(TARGET_CHAT_URL, json=payload, timeout=30)
        response.raise_for_status()

        reply = None
        try:
            data = response.json()
            reply = data.get("reply") or data.get("response") or data.get("message")
        except ValueError:
            reply = response.text.strip()

        if reply:
            await message.channel.send(reply)
            logging.info("✅ Respuesta enviada a Discord")
        else:
            logging.info("⚠️ La API devolvió respuesta vacía")

    except requests.exceptions.RequestException as e:
        logging.error("❌ Error enviando mensaje a AURA: %s", e)
        await message.channel.send("❌ No pude conectar con AURA. Revisa la configuración del bot.")

    await bot.process_commands(message)


@bot.command(name="ping", description="Comprueba que el bot de Discord está activo")
async def ping(ctx: commands.Context):
    await ctx.send("Pong! El bot está conectado.")


def main():
    if not DISCORD_TOKEN or len(DISCORD_TOKEN) < 10:
        logging.error("DISCORD_TOKEN no configurado o inválido. El bot no se iniciará.")
        return

    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
