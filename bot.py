import asyncio
import os
import base64
import zlib
import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands
from telethon import TelegramClient, events
from dotenv import load_dotenv

load_dotenv()

# ── Логирование ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("bot")

# ── Переменные окружения ───────────────────────────────────────────────────────
DISCORD_TOKEN        = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID   = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
DISCORD_CHANNEL_NAME = os.getenv("DISCORD_CHANNEL_NAME", "")

TG_API_ID        = int(os.getenv("TG_API_ID", "0"))
TG_API_HASH      = os.getenv("TG_API_HASH")
TG_SESSION       = os.getenv("TG_SESSION", "session")
TG_SESSION_B64C  = os.getenv("TG_SESSION_B64C", "")

TG_TARGET_BOT    = os.getenv("TG_TARGET_BOT", "@FunTimeEventsBot_bot")
TG_TRIGGER_MSG   = os.getenv("TG_TRIGGER_MSG", "Текущие ивенты")
TG_RESPONSE_WAIT = int(os.getenv("TG_RESPONSE_WAIT", "15"))

# ── Восстановление session.session ─────────────────────────────────────────────
session_path = f"{TG_SESSION}.session"
log.info("TG_SESSION_B64C длина: %d", len(TG_SESSION_B64C))
log.info("session.session существует: %s", os.path.exists(session_path))

if TG_SESSION_B64C:
    try:
        raw = zlib.decompress(base64.b64decode(TG_SESSION_B64C))
        with open(session_path, "wb") as f:
            f.write(raw)
        log.info("✅ session.session восстановлен (%d байт)", len(raw))
    except Exception as e:
        log.error("❌ Ошибка восстановления сессии: %s", e)
else:
    log.warning("⚠️ TG_SESSION_B64C не задан — сессия не будет восстановлена!")

# ── Discord ────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
discord_bot = commands.Bot(command_prefix="/", intents=intents)

# ── Telegram ───────────────────────────────────────────────────────────────────
tg_client = TelegramClient(TG_SESSION, TG_API_ID, TG_API_HASH)


async def fetch_events_from_tg() -> str | None:
    log.info("Запрашиваю ивенты из %s", TG_TARGET_BOT)
    try:
        target = await tg_client.get_entity(TG_TARGET_BOT)
    except Exception as e:
        log.error("Не удалось найти TG-бота: %s", e)
        return None

    future = asyncio.get_event_loop().create_future()

    @tg_client.on(events.NewMessage(from_users=target.id))
    async def _handler(event):
        if not future.done():
            future.set_result(event.message.text)

    await tg_client.send_message(target, TG_TRIGGER_MSG)

    try:
        result = await asyncio.wait_for(future, timeout=TG_RESPONSE_WAIT)
        log.info("Получен ответ (%d символов)", len(result))
        return result
    except asyncio.TimeoutError:
        log.warning("Таймаут %d сек — бот не ответил", TG_RESPONSE_WAIT)
        return None
    finally:
        tg_client.remove_event_handler(_handler)


@discord_bot.event
async def on_ready():
    log.info("Discord бот запущен: %s (id=%s)", discord_bot.user, discord_bot.user.id)


@discord_bot.command(name="event")
async def event_command(ctx: commands.Context):
    msg = await ctx.send("⏳ Запрашиваю ивенты из Telegram...")
    tg_text = await fetch_events_from_tg()
    await msg.delete()

    channel = None
    if DISCORD_CHANNEL_NAME:
        channel = discord.utils.get(ctx.guild.text_channels, name=DISCORD_CHANNEL_NAME)
    if channel is None and DISCORD_CHANNEL_ID:
        channel = discord_bot.get_channel(DISCORD_CHANNEL_ID)
    if channel is None:
        channel = ctx.channel

    if tg_text:
        embed = discord.Embed(
            title="🎉 Текущие ивенты",
            description=tg_text,
            color=0x5865F2,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Источник: {TG_TARGET_BOT}")
        await channel.send(embed=embed)
    else:
        await channel.send("❌ Бот Telegram не ответил. Попробуй позже.")


async def main():
    log.info("Запускаю Telegram клиент...")
    await tg_client.start()
    log.info("✅ Telegram подключён")
    await discord_bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
