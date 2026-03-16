import os
import asyncio
from telethon import TelegramClient

api_id = int(os.getenv("API_ID"))
api_hash = os.getenv("API_HASH")

async def main():
    client = TelegramClient("session", api_id, api_hash)
    await client.start()

    print("Userbot conectado a Telegram correctamente")

    await client.run_until_disconnected()

asyncio.run(main())
