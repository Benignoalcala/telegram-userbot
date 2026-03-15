import asyncio
import aiohttp
from telethon import TelegramClient, events

API_ID = "TU_API_ID"
API_HASH = "TU_API_HASH"
MAKE_WEBHOOK_URL = "https://hook.us1.make.com/a2p6fy2mnfc88gy9d5cokegwzfk2vg18"
SOURCE_CHANNEL = "OSINTdefender"

client = TelegramClient('session', API_ID, API_HASH)

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
