import os
import requests

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": CHAT_ID,
        "text": message
    })

if __name__ == "__main__":
    send_telegram(
        "🚨 STOCK ALERT BOT\n\n"
        "✅ Telegram connection successful!\n"
        "📊 Stock alert system is starting..."
    )
