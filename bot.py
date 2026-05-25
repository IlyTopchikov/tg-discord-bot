import os
import asyncio
import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands
from dotenv import load_dotenv
from telethon import TelegramClient, events

load_dotenv()

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# --- Переменные окружения (все как в .env) ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", 0))
TG_API_ID = int(os.getenv("TG_API_ID"))
TG_API_HASH = os.getenv("TG_API_HASH")
TG_TARGET_BOT = os.getenv("TG_TARGET_BOT", "").lstrip('@')
TG_RESPONSE_WAIT = int(os.getenv("TG_RESPONSE_WAIT", 15))
TG_SESSION = os.getenv("TG_SESSION", "session")
TG_TRIGGER_MSG = os.getenv("TG_TRIGGER_MSG", "Текущие ивенты")

# --- Telegram клиент ---
tg_client = TelegramClient(TG_SESSION, TG_API_ID, TG_API_HASH)

# Очередь для ответов от Telegram бота
response_queue = asyncio.Queue()

# --- Discord бот ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# -------------------------------------------------
# Обработчик сообщений от Telegram (кладет в очередь)
# -------------------------------------------------
@tg_client.on(events.NewMessage)
async def tg_message_handler(event):
    try:
        sender = await event.get_sender()
        if sender and (sender.username == TG_TARGET_BOT or str(sender.id) == TG_TARGET_BOT):
            if event.message.text:
                await response_queue.put(event.message.text)
                log.debug(f"Ответ от TG: {event.message.text[:100]}")
    except Exception as e:
        log.error(f"Ошибка в обработчике TG: {e}")

# -------------------------------------------------
# Функция отправки запроса и ожидания ответа
# -------------------------------------------------
async def ask_telegram(question: str):
    """Отправляет сообщение Telegram боту и возвращает ответ"""
    try:
        entity = await tg_client.get_entity(TG_TARGET_BOT)
        await tg_client.send_message(entity, question)
        log.info(f"Отправлено в Telegram: {question}")
    except Exception as e:
        log.error(f"Ошибка отправки в Telegram: {e}")
        return None
    try:
        answer = await asyncio.wait_for(response_queue.get(), timeout=TG_RESPONSE_WAIT)
        return answer
    except asyncio.TimeoutError:
        log.warning(f"Таймаут {TG_RESPONSE_WAIT} сек: {question}")
        return None

# -------------------------------------------------
# Команда /event (рабочая версия)
# -------------------------------------------------
@bot.command(name='event')
async def event_cmd(ctx, *, arg: str = None):
    msg = f"/event {arg}" if arg else TG_TRIGGER_MSG
    await ctx.send("🔄 Запрашиваю ивенты...")
    answer = await ask_telegram(msg)

    channel = bot.get_channel(DISCORD_CHANNEL_ID) or ctx.channel
    embed = discord.Embed(
        title="📅 Текущие ивенты",
        description=answer if answer else "❌ Нет ответа от Telegram бота.",
        color=0x2B2D31,
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"Источник: @{TG_TARGET_BOT}")
    await channel.send(embed=embed)

# -------------------------------------------------
# Новая команда /mine (добавлена)
# -------------------------------------------------
@bot.command(name='mine')
async def mine_cmd(ctx):
    """Отправляет 'Шахты' в Telegram бота и выводит ответ"""
    await ctx.send("⛏️ Спускаюсь в шахту...")
    # Если ваш Telegram бот не отвечает на "Шахты", замените на "/mine"
    answer = await ask_telegram("Шахты")

    channel = bot.get_channel(DISCORD_CHANNEL_ID) or ctx.channel
    if answer:
        embed = discord.Embed(
            title="⛏️ Ответ из шахты",
            description=answer,
            color=0x57F287,
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_footer(text=f"Источник: @{TG_TARGET_BOT}")
        await channel.send(embed=embed)
    else:
        await channel.send("❌ Шахта молчит. Попробуйте позже.")

# -------------------------------------------------
# Статус готовности Discord бота
# -------------------------------------------------
@bot.event
async def on_ready():
    log.info(f"✅ Discord бот {bot.user} готов (ID: {bot.user.id})")
    if DISCORD_CHANNEL_ID:
        channel = bot.get_channel(DISCORD_CHANNEL_ID)
        log.info(f"   Целевой канал: {channel.name if channel else 'не найден'}")

# -------------------------------------------------
# Запуск
# -------------------------------------------------
async def main():
    await tg_client.start()
    log.info("✅ Telegram клиент запущен и авторизован")
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Бот остановлен")
