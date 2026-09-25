import os
import requests
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# =========================
# WATCHLIST
# =========================

WATCHLIST = {
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "INFY": "INFY.NS",
    "SBIN": "SBIN.NS",
    "BHARTIARTL": "BHARTIARTL.NS",
    "ITC": "ITC.NS",
    "LT": "LT.NS",
    "TATAMOTORS": "TATAMOTORS.NS",
}

PRICE_ALERT_PERCENT = 1.0
VOLUME_SPIKE_MULTIPLIER = 2.0


# =========================
# TELEGRAM
# =========================

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=20
    )

    response.raise_for_status()


# =========================
# MARKET DATA
# =========================

def get_stock_data(symbol):
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{symbol}?interval=5m&range=1d"
    )

    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    result = data["chart"]["result"][0]

    timestamps = result["timestamp"]
    quote = result["indicators"]["quote"][0]

    closes = quote["close"]
    volumes = quote["volume"]

    clean_closes = [
        c for c in closes
        if c is not None
    ]

    clean_volumes = [
        v for v in volumes
        if v is not None
    ]

    if len(clean_closes) < 2:
        return None

    current_price = clean_closes[-1]
    previous_price = clean_closes[-2]

    price_change = (
        (current_price - previous_price)
        / previous_price
    ) * 100

    volume_spike = False

    if len(clean_volumes) >= 13:
        current_volume = clean_volumes[-1]

        previous_volumes = clean_volumes[-13:-1]

        average_volume = (
            sum(previous_volumes)
            / len(previous_volumes)
        )

        if average_volume > 0:
            volume_ratio = current_volume / average_volume

            if volume_ratio >= VOLUME_SPIKE_MULTIPLIER:
                volume_spike = True
        else:
            volume_ratio = 0
    else:
        volume_ratio = 0

    return {
        "price": current_price,
        "previous": previous_price,
        "change": price_change,
        "volume_ratio": volume_ratio,
        "volume_spike": volume_spike
    }


# =========================
# MARKET CHECK
# =========================

def check_market():

    ist = timezone(timedelta(hours=5, minutes=30))

    now = datetime.now(ist)

    # Monday-Friday only
    if now.weekday() >= 5:
        print("Market closed: Weekend")
        return

    # NSE regular market
    market_start = now.replace(
        hour=9,
        minute=15,
        second=0,
        microsecond=0
    )

    market_end = now.replace(
        hour=15,
        minute=30,
        second=0,
        microsecond=0
    )

    if now < market_start or now > market_end:
        print("Market closed:", now.strftime("%H:%M:%S"))
        return

    print("Checking market:", now.strftime("%H:%M:%S"))

    for name, symbol in WATCHLIST.items():

        try:

            data = get_stock_data(symbol)

            if not data:
                continue

            price = data["price"]
            change = data["change"]
            volume_ratio = data["volume_ratio"]

            alerts = []

            if abs(change) >= PRICE_ALERT_PERCENT:
                direction = "📈 UP" if change > 0 else "📉 DOWN"

                alerts.append(
                    f"{direction} Price movement: {change:+.2f}%"
                )

            if data["volume_spike"]:
                alerts.append(
                    f"📊 Volume spike: {volume_ratio:.1f}× average"
                )

            if alerts:

                message = (
                    "🚨 STOCK ALERT\n\n"
                    f"🏢 {name}\n"
                    f"💰 Price: ₹{price:,.2f}\n\n"
                    + "\n".join(alerts)
                    + "\n\n"
                    f"⏰ {now.strftime('%d-%m-%Y %H:%M:%S')} IST\n"
                    f"📊 NSE"
                )

                send_telegram(message)

                print("Alert sent:", name)

        except Exception as e:

            print(
                f"Error checking {name}: {e}"
            )


# =========================
# START
# =========================

if __name__ == "__main__":

    if not BOT_TOKEN or not CHAT_ID:
        raise Exception(
            "BOT_TOKEN or CHAT_ID is missing"
        )

    check_market()
