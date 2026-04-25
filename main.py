import os
import asyncio
import requests
from typing import List
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# =========================
# CONFIG
# =========================

def get_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Falta la variable de entorno obligatoria: {name}")
    return value


API_ID = int(get_env("API_ID"))
API_HASH = get_env("API_HASH")
STRING_SESSION = get_env("STRING_SESSION")
WEBHOOK_URL = get_env("WEBHOOK_URL")

# Limpia espacios, entradas vacías y normaliza a minúsculas para comparar
SOURCE_CHANNELS_RAW = get_env("SOURCE_CHANNELS")
SOURCE_CHANNELS: List[str] = [
    c.strip().lower()
    for c in SOURCE_CHANNELS_RAW.split(",")
    if c.strip()
]

if not SOURCE_CHANNELS:
    raise RuntimeError("SOURCE_CHANNELS está vacío o mal formado.")

print("Canales configurados:", SOURCE_CHANNELS)

client = TelegramClient(
    StringSession(STRING_SESSION),
    API_ID,
    API_HASH,
    auto_reconnect=True,
    connection_retries=-1,
    retry_delay=5,
    request_retries=5,
    flood_sleep_threshold=60,
)


# =========================
# HELPERS
# =========================

def post_to_make(payload: dict) -> None:
    try:
        response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
        print(f"Mensaje enviado a Make | status={response.status_code}")

        if response.status_code >= 400:
            print(f"Respuesta no OK de Make: {response.text[:500]}")
    except requests.RequestException as e:
        print(f"Error enviando mensaje a Make: {e}")


# =========================
# EVENT HANDLER
# =========================

@client.on(events.NewMessage)
async def handler(event):
    try:
        message_text = event.raw_text or ""
        chat = await event.get_chat()
        chat_username = getattr(chat, "username", None)

        print(f"RAW CHAT USERNAME: {chat_username}")
        print(f"RAW MESSAGE: {message_text[:1000]}")

        if not chat_username:
            print("IGNORADO: sin username")
            return

        chat_username_clean = chat_username.strip().lower()

        if chat_username_clean not in SOURCE_CHANNELS:
            print(f"IGNORADO: {chat_username_clean}")
            return

        print(f"ACEPTADO: {chat_username_clean}")

        message_link = f"https://t.me/{chat_username}/{event.message.id}"

       media_type = "none"

if event.message.photo:
    media_type = "photo"
elif event.message.video:
    media_type = "video"
elif event.message.document:
    media_type = "document"
elif event.message.media:
    media_type = "media"

payload = {
    "channel": chat_username,
    "message_id": event.message.id,
    "text": message_text,
    "date": str(event.message.date),
    "link": message_link,
    "has_media": media_type != "none",
    "media_type": media_type,
}

        # Requests es bloqueante; lo mandamos a hilo para no trabar el loop
        await asyncio.to_thread(post_to_make, payload)

    except Exception as e:
        print(f"Error en handler: {e}")


# =========================
# MAIN LOOP
# =========================

async def run_bot():
    await client.connect()

    if not await client.is_user_authorized():
        raise RuntimeError("La STRING_SESSION no es válida o no fue cargada correctamente.")

    me = await client.get_me()
    print("USUARIO DEL BOT:", getattr(me, "username", None), me.id)
    print("Userbot conectado a Telegram correctamente")
    print(f"Escuchando mensajes nuevos de: {SOURCE_CHANNELS}")

    await client.run_until_disconnected()


async def main():
    while True:
        try:
            await run_bot()
        except Exception as e:
            print(f"Error crítico en el bot: {e}")
            print("Reintentando en 15 segundos...")
            await asyncio.sleep(15)


if __name__ == "__main__":
    asyncio.run(main())
