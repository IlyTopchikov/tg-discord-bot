import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

load_dotenv()

TG_API_ID   = int(os.getenv("TG_API_ID", "0"))
TG_API_HASH = os.getenv("TG_API_HASH")
TG_SESSION  = os.getenv("TG_SESSION", "session")


def print_qr(url: str):
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        qr.print_ascii(invert=True)
    except ImportError:
        print("(установи qrcode: pip install qrcode)")
        print(f"Ссылка: {url}")


async def main():
    client = TelegramClient(TG_SESSION, TG_API_ID, TG_API_HASH)
    await client.connect()

    qr_login = await client.qr_login()

    print("\n📱 Сканируй QR ниже через Telegram:")
    print("   Настройки → Устройства → Подключить устройство\n")
    print_qr(qr_login.url)
    print("\n⏳ Жду сканирования (60 сек)...")

    try:
        await qr_login.wait(60)
    except SessionPasswordNeededError:
        pwd = input("\n🔐 Введи пароль двухфакторной аутентификации Telegram: ")
        await client.sign_in(password=pwd)
    except Exception as e:
        print(f"Ошибка: {e}")
        return

    me = await client.get_me()
    print(f"\n✅ Авторизован как: {me.first_name} (@{me.username})")
    print(f"   Файл сессии: {TG_SESSION}.session\n")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())