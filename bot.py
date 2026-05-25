import asyncio
import os
import logging
from datetime import datetime, timezone


import discord
from discord.ext import commands
from telethon import TelegramClient, events
from telethon.tl.types import User
from dotenv import load_dotenv

load_dotenv()

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("bot")

# ── Config from .env ───────────────────────────────────────────────────────────
DISCORD_TOKEN      = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID   = int(os.getenv("DISCORD_CHANNEL_ID", "0"))
DISCORD_CHANNEL_NAME = os.getenv("DISCORD_CHANNEL_NAME", "")  # например: ивенты
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_API_ID   = int(os.getenv("TG_API_ID", "0"))
TG_API_HASH = os.getenv("TG_API_HASH")
TG_SESSION  = os.getenv("TG_SESSION", "session")

TG_TARGET_BOT    = os.getenv("TG_TARGET_BOT", "@FunTimeEventsBot_bot")
TG_TRIGGER_MSG   = os.getenv("TG_TRIGGER_MSG", "Текущие ивенты")
TG_RESPONSE_WAIT = int(os.getenv("TG_RESPONSE_WAIT", "15"))  # секунд ожидания

# ── Discord setup ──────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
discord_bot = commands.Bot(command_prefix="/", intents=intents)

# ── Telegram setup ─────────────────────────────────────────────────────────────
tg_client = TelegramClient(TG_SESSION, TG_API_ID, TG_API_HASH)

# Очередь для передачи ответа от TG в Discord
response_queue: asyncio.Queue = asyncio.Queue()


async def fetch_events_from_tg() -> str | None:
    """
    Отправляет сообщение-триггер боту в Telegram и ждёт его ответа.
    Возвращает текст ответа или None при таймауте.
    """
    log.info("Отправляю '%s' → %s", TG_TRIGGER_MSG, TG_TARGET_BOT)

    # Получаем entity бота
    try:
        target = await tg_client.get_entity(TG_TARGET_BOT)
    except Exception as exc:
        log.error("Не удалось получить entity бота TG: %s", exc)
        return None

    bot_id = target.id

    # Временный обработчик — ловит первый ответ от нужного бота
    future: asyncio.Future = asyncio.get_event_loop().create_future()

    @tg_client.on(events.NewMessage(from_users=bot_id))
    async def _handler(event):
        if not future.done():
            future.set_result(event.message.text)

    await tg_client.send_message(target, TG_TRIGGER_MSG)

    try:
        result = await asyncio.wait_for(future, timeout=TG_RESPONSE_WAIT)
        log.info("Получен ответ от TG-бота (%d символов)", len(result))
        return result
    except asyncio.TimeoutError:
        log.warning("Таймаут: бот TG не ответил за %d сек.", TG_RESPONSE_WAIT)
        return None
    finally:
        tg_client.remove_event_handler(_handler)


# ── Discord команды ────────────────────────────────────────────────────────────
@discord_bot.event
async def on_ready():
    log.info("Discord бот запущен как %s (id=%s)", discord_bot.user, discord_bot.user.id)


@discord_bot.command(name="event")
async def event_command(ctx: commands.Context):
    """Получает текущие ивенты из Telegram и постит в канал Discord."""
    # Отвечаем сразу, чтобы пользователь знал — запрос принят
    waiting_msg = await ctx.send("⏳ Запрашиваю ивенты из Telegram, подождите...")

    tg_text = await fetch_events_from_tg()

    await waiting_msg.delete()

    # Ищем канал: сначала по названию, потом по ID, иначе текущий канал
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
        await channel.send(
            "❌ Не удалось получить ивенты — бот Telegram не ответил. "
            "Попробуй чуть позже или увеличь `TG_RESPONSE_WAIT` в `.env`."
        )


# ── Запуск ─────────────────────────────────────────────────────────────────────
async def main():
    # Сначала подключаемся к Telegram
    await tg_client.start(bot_token=TG_BOT_TOKEN)
    log.info("Telegram клиент подключён")

    # Потом запускаем Discord бота
    await discord_bot.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
