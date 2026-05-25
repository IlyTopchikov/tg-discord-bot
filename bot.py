import os
import asyncio
import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands
from dotenv import load_dotenv
from telethon import TelegramClient, events

load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# --- Чтение переменных окружения ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", 0))
TG_API_ID = int(os.getenv("TG_API_ID"))
TG_API_HASH = os.getenv("TG_API_HASH")
TG_TARGET_BOT = os.getenv("TG_TARGET_BOT", "").lstrip('@')  # убираем @, если есть
TG_RESPONSE_WAIT = int(os.getenv("TG_RESPONSE_WAIT", 15))
TG_SESSION = os.getenv("TG_SESSION", "session")
TG_TRIGGER_MSG = os.getenv("TG_TRIGGER_MSG", "Текущие ивенты")

# --- Telegram клиент ---
tg_client = TelegramClient(TG_SESSION, TG_API_ID, TG_API_HASH)

# --- Discord бот ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Очередь для ответов от Telegram
response_queue = asyncio.Queue()

# -------------------------------------------------
# Обработчик сообщений от Telegram
# -------------------------------------------------
@tg_client.on(events.NewMessage)
async def tg_handler(event):
    try:
        sender = await event.get_sender()
        # Проверяем, что сообщение пришло от нужного бота
        if sender and (sender.username == TG_TARGET_BOT or str(sender.id) == TG_TARGET_BOT):
            text = event.message.text
            if text:
                log.info(f"Получен ответ от {TG_TARGET_BOT}: {text[:100]}")
                await response_queue.put(text)
    except Exception as e:
        log.error(f"Ошибка в обработчике Telegram: {e}")

# -------------------------------------------------
# Функция отправки запроса в Telegram и ожидания ответа
# -------------------------------------------------
async def ask_telegram(question: str) -> str | None:
    """Отправляет сообщение Telegram-боту и возвращает ответ."""
    try:
        entity = await tg_client.get_entity(TG_TARGET_BOT)
        await tg_client.send_message(entity, question)
        log.info(f"Отправлено в Telegram: {question}")
    except Exception as e:
        log.error(f"Не удалось отправить '{question}': {e}")
        return None

    try:
        answer = await asyncio.wait_for(response_queue.get(), timeout=TG_RESPONSE_WAIT)
        return answer
    except asyncio.TimeoutError:
        log.warning(f"Таймаут {TG_RESPONSE_WAIT} сек при запросе: {question}")
        return None

# -------------------------------------------------
# Команда /event
# -------------------------------------------------
@bot.command(name='event')
async def event_cmd(ctx, *, arg: str = None):
    if arg:
        msg = f"/event {arg}"
    else:
        msg = TG_TRIGGER_MSG   # используем "Текущие ивенты" из .env
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
# Команда /mine (новая)
# -------------------------------------------------
@bot.command(name='mine')
async def mine_cmd(ctx):
    """Отправляет 'Шахты' в Telegram-бота и выводит ответ."""
    await ctx.send("⛏️ Спускаюсь в шахту...")
    # Отправляем слово "Шахты". Если бот не отвечает, замените на "/mine"
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
# Статус запуска Discord бота
# -------------------------------------------------
@bot.event
async def on_ready():
    log.info(f"✅ Discord бот {bot.user} готов (ID: {bot.user.id})")
    log.info(f"   Канал для постов: {DISCORD_CHANNEL_ID}")
    log.info(f"   Telegram бот: @{TG_TARGET_BOT}")

# -------------------------------------------------
# Главная функция запуска
# -------------------------------------------------
async def main():
    await tg_client.start()
    log.info("✅ Telegram клиент запущен и авторизован")
    await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Бот остановлен вручную")
