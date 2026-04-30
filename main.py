import os
import asyncio
import requests
from typing import List, Dict, Optional
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# =========================
# CONFIG
# =========================

def get_env(name: str, required: bool = True) -> str:
    value = os.getenv(name, "").strip()
    if required and not value:
        raise RuntimeError(f"Falta la variable de entorno obligatoria: {name}")
    return value


API_ID = int(get_env("API_ID"))
API_HASH = get_env("API_HASH")
STRING_SESSION = get_env("STRING_SESSION")

# =========================
# WEBHOOKS
# =========================

# MODO 1: Un solo webhook (compatibilidad)
WEBHOOK_URL = get_env("WEBHOOK_URL", required=False)

# MODO 2: Múltiples webhooks separados por coma
WEBHOOK_URLS_RAW = get_env("WEBHOOK_URLS", required=False)

# MODO 3: Webhooks nombrados
WEBHOOK_PROD = get_env("WEBHOOK_PROD", required=False)
WEBHOOK_DEV = get_env("WEBHOOK_DEV", required=False)
WEBHOOK_CLIENT1 = get_env("WEBHOOK_CLIENT1", required=False)
WEBHOOK_CLIENT2 = get_env("WEBHOOK_CLIENT2", required=False)
WEBHOOK_CLIENT3 = get_env("WEBHOOK_CLIENT3", required=False)

WEBHOOKS: List[Dict[str, str]] = []

if WEBHOOK_URL:
    WEBHOOKS.append({"name": "WEBHOOK_URL", "url": WEBHOOK_URL})

if WEBHOOK_URLS_RAW:
    urls = [u.strip() for u in WEBHOOK_URLS_RAW.split(",") if u.strip()]
    for i, url in enumerate(urls, 1):
        WEBHOOKS.append({"name": f"WEBHOOK_{i}", "url": url})

if WEBHOOK_PROD:
    WEBHOOKS.append({"name": "WEBHOOK_PROD", "url": WEBHOOK_PROD})

if WEBHOOK_DEV:
    WEBHOOKS.append({"name": "WEBHOOK_DEV", "url": WEBHOOK_DEV})

if WEBHOOK_CLIENT1:
    WEBHOOKS.append({"name": "WEBHOOK_CLIENT1", "url": WEBHOOK_CLIENT1})

if WEBHOOK_CLIENT2:
    WEBHOOKS.append({"name": "WEBHOOK_CLIENT2", "url": WEBHOOK_CLIENT2})

if WEBHOOK_CLIENT3:
    WEBHOOKS.append({"name": "WEBHOOK_CLIENT3", "url": WEBHOOK_CLIENT3})


# =========================
# EVITAR WEBHOOKS DUPLICADOS
# =========================

unique_urls = set()
clean_webhooks: List[Dict[str, str]] = []

for wh in WEBHOOKS:
    url = wh["url"].strip()

    if url in unique_urls:
        print(f"⚠️ Webhook duplicado ignorado: {wh['name']} -> {url[:50]}...")
        continue

    unique_urls.add(url)
    clean_webhooks.append({"name": wh["name"], "url": url})

WEBHOOKS = clean_webhooks


if not WEBHOOKS:
    raise RuntimeError(
        "No se configuró ningún webhook. Usa WEBHOOK_URL, WEBHOOK_URLS, "
        "o webhooks nombrados como WEBHOOK_PROD, WEBHOOK_DEV, WEBHOOK_CLIENT1."
    )

print(f"✅ Webhooks configurados: {len(WEBHOOKS)}")
for wh in WEBHOOKS:
    print(f"   - {wh['name']}: {wh['url'][:50]}...")


# =========================
# CANALES FUENTE
# =========================

SOURCE_CHANNELS_RAW = get_env("SOURCE_CHANNELS")
SOURCE_CHANNELS: List[str] = [
    c.strip().lower()
    for c in SOURCE_CHANNELS_RAW.split(",")
    if c.strip()
]

if not SOURCE_CHANNELS:
    raise RuntimeError("SOURCE_CHANNELS está vacío o mal formado.")

print(f"✅ Canales configurados: {SOURCE_CHANNELS}")


# =========================
# FILTROS OPCIONALES POR WEBHOOK
# =========================

# Formato:
# WEBHOOK_PROD_CHANNELS=canal1,canal2
# WEBHOOK_DEV_CHANNELS=canal1,canal2
# WEBHOOK_CLIENT1_CHANNELS=canal1,canal2
#
# Si no se define, ese webhook recibe mensajes de todos los canales.

WEBHOOK_FILTERS: Dict[str, Optional[List[str]]] = {}

for wh in WEBHOOKS:
    filter_var = f"{wh['name']}_CHANNELS"
    filter_value = get_env(filter_var, required=False)

    if filter_value:
        channels = [
            c.strip().lower()
            for c in filter_value.split(",")
            if c.strip()
        ]
        WEBHOOK_FILTERS[wh["name"]] = channels
        print(f"   📌 {wh['name']} filtrado a: {channels}")
    else:
        WEBHOOK_FILTERS[wh["name"]] = None


# =========================
# TELEGRAM CLIENT
# =========================

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

def post_to_webhook(webhook_name: str, webhook_url: str, payload: dict) -> None:
    try:
        response = requests.post(webhook_url, json=payload, timeout=30)
        status = "✅" if response.status_code < 400 else "❌"
        print(f"{status} {webhook_name} | status={response.status_code}")

        if response.status_code >= 400:
            print(f"   ⚠️ Respuesta: {response.text[:200]}")

    except requests.RequestException as e:
        print(f"❌ Error en {webhook_name}: {e}")


def should_send_to_webhook(webhook_name: str, channel: str) -> bool:
    filter_channels = WEBHOOK_FILTERS.get(webhook_name)

    if filter_channels is None:
        return True

    return channel in filter_channels


async def broadcast_to_webhooks(payload: dict, channel: str) -> None:
    tasks = []

    for wh in WEBHOOKS:
        if should_send_to_webhook(wh["name"], channel):
            payload_copy = payload.copy()
            payload_copy["webhook_name"] = wh["name"]

            task = asyncio.to_thread(
                post_to_webhook,
                wh["name"],
                wh["url"],
                payload_copy
            )
            tasks.append(task)

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    else:
        print(f"⚠️ No hay webhooks habilitados para el canal: {channel}")


# =========================
# EVENT HANDLER
# =========================

@client.on(events.NewMessage)
async def handler(event):
    try:
        message_text = event.raw_text or ""
        chat = await event.get_chat()
        chat_username = getattr(chat, "username", None)

        if not chat_username:
            return

        chat_username_clean = chat_username.strip().lower()

        if chat_username_clean not in SOURCE_CHANNELS:
            return

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

        print(f"\n📨 Nuevo mensaje de @{chat_username} | ID: {event.message.id} | media: {media_type}")

        await broadcast_to_webhooks(payload, chat_username_clean)

    except Exception as e:
        print(f"❌ Error en handler: {e}")


# =========================
# MAIN LOOP
# =========================

async def run_bot():
    await client.connect()

    if not await client.is_user_authorized():
        raise RuntimeError("La STRING_SESSION no es válida o no fue cargada correctamente.")

    me = await client.get_me()

    print("\n" + "=" * 60)
    print("🤖 TELEGRAM USERBOT MULTI-WEBHOOK")
    print("=" * 60)
    print(f"👤 Usuario: @{getattr(me, 'username', 'N/A')} | ID: {me.id}")
    print(f"📡 Webhooks activos: {len(WEBHOOKS)}")
    print(f"📢 Canales escuchando: {len(SOURCE_CHANNELS)}")
    print("=" * 60)
    print("✅ Bot conectado y listo\n")

    await client.run_until_disconnected()


async def main():
    while True:
        try:
            await run_bot()
        except Exception as e:
            print(f"❌ Error crítico: {e}")
            print("🔄 Reintentando en 15 segundos...")
            await asyncio.sleep(15)


if __name__ == "__main__":
    asyncio.run(main())
