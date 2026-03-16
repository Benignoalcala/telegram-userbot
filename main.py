
import os
import asyncio
import aiohttp
from telethon import TelegramClient, events

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
MAKE_WEBHOOK_URL = os.getenv("WEBHOOK_URL")
SOURCE_CHANNEL = os.getenv("SOURCE_CHANNEL", "OSINTdefender")

client = TelegramClient("session", API_ID, API_HASH)

@client.on(events.NewMessage(chats=SOURCE_CHANNEL))
async def handler(event):
    message = event.message.message
    if message:
        async with aiohttp.ClientSession() as session:
            await session.post(MAKE_WEBHOOK_URL, json={"message": message})

async def main():
    await client.start()
    print("Userbot corriendo...")
    await client.run_until_disconnected()

asyncio.run(main())
