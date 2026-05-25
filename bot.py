import os
import asyncio
import logging
from dotenv import load_dotenv

import discord
from discord.ext import commands
from telethon import TelegramClient, events

# Загрузка переменных из .env
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Переменные окружения
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_CHANNEL_ID = int(os.getenv("DISCORD_CHANNEL_ID", 0))
TG_API_ID = int(os.getenv("TG_API_ID"))
TG_API_HASH = os.getenv("TG_API_HASH")
TG_TARGET_BOT = os.getenv("TG_TARGET_BOT")   # например: FunTimeEventsBot_bot
TG_RESPONSE_WAIT = int(os.getenv("TG_RESPONSE_WAIT", 15))

# Очередь для ответов от Telegram
response_queue = asyncio.Queue()

# Telegram клиент (используем существующий файл сессии "session")
tg_client = TelegramClient("session", TG_API_ID, TG_API_HASH)

# ---------- Discord бот ----------
class DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='/', intents=intents)
        self.response_wait = TG_RESPONSE_WAIT

    async def on_ready(self):
        logger.info(f"✅ Discord бот {self.user} готов")

    async def wait_for_response(self, timeout=None):
        """Ожидает ответ из очереди response_queue"""
        if timeout is None:
            timeout = self.response_wait
        try:
            return await asyncio.wait_for(response_queue.get(), timeout=timeout)
        except asyncio.TimeoutError:
            logger.error("Таймаут ожидания ответа от Telegram")
            raise

    async def send_to_telegram(self, text: str):
        """Отправляет текст в Telegram боту"""
        if not tg_client or not tg_client.is_connected():
            logger.error("Telegram клиент не подключён")
            return
        try:
            await tg_client.send_message(TG_TARGET_BOT, text)
            logger.info(f"Отправлено в Telegram: {text}")
        except Exception as e:
            logger.exception("Ошибка отправки в Telegram")

    # ---------- Команда /event ----------
    @commands.command(name='event')
    async def event(self, ctx, *, arg: str = None):
        """Отправляет /event в Telegram и пересылает ответ"""
        msg = f"/event {arg}" if arg else "/event"
        await self.send_to_telegram(msg)
        try:
            response = await self.wait_for_response()
            await ctx.send(f"```\n{response}\n```")
        except asyncio.TimeoutError:
            await ctx.send(f"❌ Telegram бот не ответил за {self.response_wait} сек.")

    # ---------- Команда /mine (НОВАЯ) ----------
    @commands.command(name='mine')
    async def mine(self, ctx):
        """Отправляет 'Шахты' в Telegram и пересылает ответ"""
        msg = "Шахты"
        await self.send_to_telegram(msg)
        try:
            response = await self.wait_for_response()
            await ctx.send(f"```\n{response}\n```")
        except asyncio.TimeoutError:
            await ctx.send(f"❌ Telegram бот не ответил на 'Шахты' за {self.response_wait} сек.")
        except Exception as e:
            await ctx.send(f"⚠️ Ошибка: {e}")

# ---------- Обработчик сообщений Telegram ----------
@tg_client.on(events.NewMessage(chats=TG_TARGET_BOT))
async def telegram_handler(event):
    """Получает ответ от Telegram бота и кладёт в очередь"""
    if event.message.text:
        logger.info(f"Получен ответ от Telegram: {event.message.text[:50]}...")
        await response_queue.put(event.message.text)

# ---------- Запуск ----------
async def main():
    # Запускаем Telegram клиента
    await tg_client.start()
    logger.info("✅ Telegram клиент запущен")

    # Запускаем Discord бота
    bot = DiscordBot()
    async with bot:
        await bot.start(DISCORD_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
