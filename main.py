import os
import asyncio
import requests
from telethon import TelegramClient, events
from telethon.sessions import StringSession

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
STRING_SESSION = os.environ["STRING_SESSION"]
SOURCE_CHANNELS = [c.strip() for c in os.environ["SOURCE_CHANNELS"].split(",")]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)


@@client.on(events.NewMessage)
async def handler(event):
    try:
        message_text = event.raw_text or ""
        chat = await event.get_chat()
        chat_username = getattr(chat, "username", None)

        if not chat_username:
            return

        if chat_username.lower() not in [c.lower() for c in SOURCE_CHANNELS]:
            print(f"IGNORADO: {chat_username}")
            return

        print(f"ACEPTADO: {chat_username}")

        message_link = f"https://t.me/{chat_username}/{event.message.id}"

        payload = {
            "channel": chat_username,
            "message_id": event.message.id,
            "text": message_text,
            "date": str(event.message.date),
            "link": message_link
        }

        response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
        print(f"Mensaje enviado a Make | status={response.status_code}")

    except Exception as e:
        print(f"Error enviando mensaje a Make: {e}")


async def main():
    await client.start()

    me = await client.get_me()
    print("USUARIO DEL BOT:", me.username, me.id)

    print("Userbot conectado a Telegram correctamente")
    print(f"Escuchando mensajes nuevos de: {SOURCE_CHANNELS}")

    await client.run_until_disconnected()


asyncio.run(main())
