import os
import requests
from datetime import datetime, timezone, timedelta

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# NIFTY 50 watchlist
WATCHLIST = {
    "ADANIENTERPRISES": "ADANIENT.NS",
    "ADANIPORTS": "ADANIPORTS.NS",
    "APOLLOHOSP": "APOLLOHOSP.NS",
    "ASIANPAINT": "ASIANPAINT.NS",
    "AXISBANK": "AXISBANK.NS",
    "BAJAJ-AUTO": "BAJAJ-AUTO.NS",
    "BAJAJFINSV": "BAJAJFINSV.NS",
    "BAJFINANCE": "BAJFINANCE.NS",
    "BEL": "BEL.NS",
    "BHARTIARTL": "BHARTIARTL.NS",
    "CIPLA": "CIPLA.NS",
    "COALINDIA": "COALINDIA.NS",
    "DRREDDY": "DRREDDY.NS",
    "EICHERMOT": "EICHERMOT.NS",
    "ETERNAL": "ETERNAL.NS",
    "GRASIM": "GRASIM.NS",
    "HCLTECH": "HCLTECH.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "HDFCLIFE": "HDFCLIFE.NS",
    "HEROMOTOCO": "HEROMOTOCO.NS",
    "HINDALCO": "HINDALCO.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "INDUSINDBK": "INDUSINDBK.NS",
    "INFY": "INFY.NS",
    "ITC": "ITC.NS",
    "JIOFIN": "JIOFIN.NS",
    "JSWSTEEL": "JSWSTEEL.NS",
    "KOTAKBANK": "KOTAKBANK.NS",
    "LT": "LT.NS",
    "M&M": "M&M.NS",
    "MARUTI": "MARUTI.NS",
    "MAXHEALTH": "MAXHEALTH.NS",
    "NESTLEIND": "NESTLEIND.NS",
    "NTPC": "NTPC.NS",
    "ONGC": "ONGC.NS",
    "POWERGRID": "POWERGRID.NS",
    "RELIANCE": "RELIANCE.NS",
    "SBILIFE": "SBILIFE.NS",
    "SBIN": "SBIN.NS",
    "SHRIRAMFIN": "SHRIRAMFIN.NS",
    "SUNPHARMA": "SUNPHARMA.NS",
    "TATACONSUM": "TATACONSUM.NS",
    "TATAMOTORS": "TATAMOTORS.NS",
    "TATASTEEL": "TATASTEEL.NS",
    "TECHM": "TECHM.NS",
    "TITAN": "TITAN.NS",
    "TRENT": "TRENT.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS",
    "WIPRO": "WIPRO.NS",
    "TMPV": "TMPV.NS",
}

PRICE_ALERT_PERCENT = 1.0
VOLUME_SPIKE_MULTIPLIER = 2.0


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

    quote = result["indicators"]["quote"][0]

    closes = quote.get("close", [])
    volumes = quote.get("volume", [])

    clean_closes = [x for x in closes if x is not None]
    clean_volumes = [x for x in volumes if x is not None]

    if len(clean_closes) < 2:
        return None

    current_price = clean_closes[-1]
    previous_price = clean_closes[-2]

    change = (
        (current_price - previous_price)
        / previous_price
    ) * 100

    volume_ratio = 0

    if len(clean_volumes) >= 13:
        current_volume = clean_volumes[-1]
        previous_volumes = clean_volumes[-13:-1]

        average_volume = (
            sum(previous_volumes)
            / len(previous_volumes)
        )

        if average_volume > 0:
            volume_ratio = current_volume / average_volume

    return {
        "price": current_price,
        "change": change,
        "volume_ratio": volume_ratio
    }


def check_market():

    ist = timezone(timedelta(hours=5, minutes=30))
    now = datetime.now(ist)

    # Monday-Friday
    if now.weekday() >= 5:
        print("Weekend - market closed")
        return

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

    print(
        "Scanning NIFTY 50:",
        now.strftime("%d-%m-%Y %H:%M:%S")
    )

    alerts_sent = 0

    for name, symbol in WATCHLIST.items():

        try:

            data = get_stock_data(symbol)

            if not data:
                continue

            price = data["price"]
            change = data["change"]
            volume_ratio = data["volume_ratio"]

            alert_lines = []

            if abs(change) >= PRICE_ALERT_PERCENT:

                direction = "📈 UP" if change > 0 else "📉 DOWN"

                alert_lines.append(
                    f"{direction}: {change:+.2f}%"
                )

            if volume_ratio >= VOLUME_SPIKE_MULTIPLIER:

                alert_lines.append(
                    f"📊 Volume: {volume_ratio:.1f}× average"
                )

            if alert_lines:

                message = (
                    "🚨 NIFTY 50 STOCK ALERT\n\n"
                    f"🏢 {name}\n"
                    f"💰 ₹{price:,.2f}\n\n"
                    + "\n".join(alert_lines)
                    + "\n\n"
                    f"⏰ {now.strftime('%H:%M:%S')} IST\n"
                    "📊 Data: Yahoo Finance\n"
                    "⚠️ Informational alert"
                )

                send_telegram(message)

                alerts_sent += 1
                print("Alert sent:", name)

        except Exception as error:

            print(
                f"{name} error: {error}"
            )

    print(
        f"Scan completed. Alerts sent: {alerts_sent}"
    )


if __name__ == "__main__":

    if not BOT_TOKEN or not CHAT_ID:
        raise Exception(
            "BOT_TOKEN or CHAT_ID is missing"
        )

    send_telegram(
        "🟢 NIFTY 50 SCANNER\n\n"
        "GitHub Actions is running.\n"
        "Starting market scan..."
    )

    check_market()
