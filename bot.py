import os
import asyncio
import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands
from dotenv import load_dotenv
from telethon import TelegramClient, events

# Загружаем переменные окружения из файла .env
load_dotenv()

# Настройка логирования (для отладки)
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# --- Переменные окружения ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", 0))
TG_API_ID = int(os.getenv("TG_API_ID"))
TG_API_HASH = os.getenv("TG_API_HASH")
TG_TARGET_BOT = os.getenv("TG_TARGET_BOT")   # например: FunTimeEventsBot_bot
TG_RESPONSE_WAIT = int(os.getenv("TG_RESPONSE_WAIT", 15))

# --- Глобальная очередь для ответов от Telegram ---
response_queue = asyncio.Queue()

# --- Telegram клиент (используем существующий файл сессии) ---
tg_client = TelegramClient("session", TG_API_ID, TG_API_HASH)

# --- Discord бот ---
discord_bot = commands.Bot(command_prefix='/', intents=discord.Intents.all())

# ================= ОБРАБОТЧИК СООБЩЕНИЙ ОТ TELEGRAM =================
@tg_client.on(events.NewMessage)
async def telegram_message_handler(event):
    """Слушаем все сообщения. Если они от нужного бота — кладём в очередь."""
    try:
        sender = await event.get_sender()
        if sender and getattr(sender, 'username', None) == TG_TARGET_BOT.lstrip('@'):
            text = event.message.text
            if text:
                log.info(f"Получен ответ от Telegram: {text[:100]}")
                await response_queue.put(text)
    except Exception as e:
        log.error(f"Ошибка в обработчике Telegram: {e}")

# ================= КОМАНДЫ DISCORD =================
@discord_bot.event
async def on_ready():
    log.info(f"✅ Discord бот {discord_bot.user} запущен и готов!")

async def send_to_telegram_and_wait(message: str) -> str | None:
    """Отправляет сообщение в Telegram-бота и ожидает ответа из очереди."""
    try:
        target = await tg_client.get_entity(TG_TARGET_BOT)
        await tg_client.send_message(target, message)
        log.info(f"Отправлено в Telegram: {message}")
    except Exception as e:
        log.error(f"Не удалось отправить сообщение в Telegram: {e}")
        return None

    try:
        response = await asyncio.wait_for(response_queue.get(), timeout=TG_RESPONSE_WAIT)
        return response
    except asyncio.TimeoutError:
        log.warning(f"Таймаут {TG_RESPONSE_WAIT} сек — Telegram бот не ответил на '{message}'")
        return None

@discord_bot.command(name="event")
async def event_command(ctx, *, arg: str = None):
    """Отправляет /event (с аргументом или без) в Telegram и показывает ответ."""
    msg = f"/event {arg}" if arg else "/event"
    await ctx.send("🔄 Обрабатываю запрос `/event`...")
    response = await send_to_telegram_and_wait(msg)

    channel = discord_bot.get_channel(DISCORD_CHANNEL_ID) or ctx.channel
    embed = discord.Embed(
        title="📅 Текущие ивенты",
        description=response if response else "❌ Не удалось получить ответ от Telegram бота.",
        color=0x2B2D31,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=f"Источник: {TG_TARGET_BOT}")
    await channel.send(embed=embed)

@discord_bot.command(name="mine")
async def mine_command(ctx):
    """Отправляет 'Шахты' в Telegram-бота и пересылает ответ."""
    await ctx.send("⛏️ Спускаюсь в шахту, ищу ответ...")
    response = await send_to_telegram_and_wait("Шахты")

    channel = discord_bot.get_channel(DISCORD_CHANNEL_ID) or ctx.channel
    if response:
        embed = discord.Embed(
            title="⛏️ Результат из шахты",
            description=response,
            color=0x57F287,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_footer(text=f"Источник: {TG_TARGET_BOT}")
        await channel.send(embed=embed)
    else:
        await channel.send("❌ Шахта молчит. Попробуй позже.")

# ================= ЗАПУСК =================
async def main():
    # Запускаем Telegram клиента
    await tg_client.start()
    log.info("✅ Telegram клиент авторизован и готов")

    # Запускаем Discord бота
    await discord_bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Бот остановлен вручную")
