import os
import requests
from datetime import datetime, time
from urllib.parse import quote
from zoneinfo import ZoneInfo


# ============================================================
# TELEGRAM SETTINGS
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")


# ============================================================
# NIFTY 50 WATCHLIST
# ============================================================

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
    "TMPV": "TMPV.NS",
    "TATASTEEL": "TATASTEEL.NS",
    "TECHM": "TECHM.NS",
    "TITAN": "TITAN.NS",
    "TRENT": "TRENT.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS",
    "WIPRO": "WIPRO.NS",
}


# ============================================================
# ALERT SETTINGS
# ============================================================

PRICE_ALERT_PERCENT = 1.0
VOLUME_SPIKE_MULTIPLIER = 2.0


# ============================================================
# TELEGRAM FUNCTION
# ============================================================

def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram credentials are missing.")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    try:
        response = requests.post(
            url,
            data=payload,
            timeout=15
        )

        if response.status_code == 200:
            print("Telegram message sent successfully.")
            return True

        print(
            f"Telegram error: "
            f"{response.status_code} - {response.text}"
        )

    except Exception as e:
        print(f"Telegram connection error: {e}")

    return False


# ============================================================
# GET STOCK DATA FROM YAHOO FINANCE
# ============================================================

def get_stock_data(symbol):

    try:
        encoded_symbol = quote(symbol, safe="")

        url = (
            "https://query1.finance.yahoo.com/v8/finance/chart/"
            f"{encoded_symbol}"
        )

        params = {
            "interval": "5m",
            "range": "1d"
        }

        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=15
        )

        if response.status_code != 200:
            print(
                f"{symbol} error: "
                f"{response.status_code} "
                f"{response.text[:200]}"
            )
            return None

        data = response.json()

        result = data.get("chart", {}).get("result")

        if not result:
            print(f"{symbol}: No data returned.")
            return None

        result = result[0]

        timestamps = result.get("timestamp")
        indicators = result.get("indicators", {})
        quote_data = indicators.get("quote", [])

        if not timestamps or not quote_data:
            print(f"{symbol}: Incomplete data.")
            return None

        quote_data = quote_data[0]

        closes = quote_data.get("close", [])
        volumes = quote_data.get("volume", [])

        valid_data = []

        for i in range(len(timestamps)):

            if i >= len(closes):
                continue

            close = closes[i]

            if close is None:
                continue

            volume = 0

            if i < len(volumes) and volumes[i] is not None:
                volume = volumes[i]

            valid_data.append(
                {
                    "timestamp": timestamps[i],
                    "close": float(close),
                    "volume": float(volume)
                }
            )

        if len(valid_data) < 2:
            print(f"{symbol}: Not enough data.")
            return None

        return valid_data

    except Exception as e:
        print(f"{symbol} error: {e}")
        return None


# ============================================================
# MARKET HOURS CHECK
# ============================================================

def is_market_open():

    india_time = datetime.now(
        ZoneInfo("Asia/Kolkata")
    )

    weekday = india_time.weekday()

    # Monday = 0
    # Sunday = 6

    if weekday >= 5:
        return False

    current_time = india_time.time()

    market_start = time(9, 15)
    market_end = time(15, 30)

    return market_start <= current_time <= market_end


# ============================================================
# MARKET SCANNER
# ============================================================

def check_market():

    india_time = datetime.now(
        ZoneInfo("Asia/Kolkata")
    )

    print(
        "Scanning NIFTY 50: "
        f"{india_time.strftime('%d-%m-%Y %H:%M:%S')}"
    )

    if not is_market_open():

        print("Market is currently closed.")

        return

    alerts_sent = 0
    successful_stocks = 0
    failed_stocks = 0

    for stock_name, symbol in WATCHLIST.items():

        data = get_stock_data(symbol)

        if not data:
            failed_stocks += 1
            continue

        successful_stocks += 1

        # Latest candle
        latest = data[-1]

        # Previous candle
        previous = data[-2]

        latest_price = latest["close"]
        previous_price = previous["close"]

        if previous_price <= 0:
            continue

        # ====================================================
        # PRICE CHANGE
        # ====================================================

        price_change = (
            (latest_price - previous_price)
            / previous_price
        ) * 100

        # ====================================================
        # VOLUME SPIKE
        # ====================================================

        recent_volumes = []

        for item in data[:-1]:

            volume = item["volume"]

            if volume > 0:
                recent_volumes.append(volume)

        if len(recent_volumes) > 10:
            recent_volumes = recent_volumes[-10:]

        average_volume = 0

        if recent_volumes:
            average_volume = (
                sum(recent_volumes)
                / len(recent_volumes)
            )

        latest_volume = latest["volume"]

        volume_ratio = 0

        if average_volume > 0:
            volume_ratio = (
                latest_volume
                / average_volume
            )

        # ====================================================
        # ALERT CONDITIONS
        # ====================================================

        price_alert = (
            abs(price_change)
            >= PRICE_ALERT_PERCENT
        )

        volume_alert = (
            volume_ratio
            >= VOLUME_SPIKE_MULTIPLIER
        )

        if not price_alert and not volume_alert:
            continue

        # ====================================================
        # ALERT TYPE
        # ====================================================

        if price_change > 0:
            direction = "🟢 UP"
        elif price_change < 0:
            direction = "🔴 DOWN"
        else:
            direction = "⚪ FLAT"

        reasons = []

        if price_alert:
            reasons.append(
                f"Price move: {price_change:+.2f}%"
            )

        if volume_alert:
            reasons.append(
                f"Volume: {volume_ratio:.1f}x average"
            )

        reason_text = "\n".join(reasons)

        # ====================================================
        # TELEGRAM MESSAGE
        # ====================================================

        message = (
            "🚨 STOCK MARKET ALERT\n\n"
            f"📊 Stock: {stock_name}\n"
            f"💰 Price: ₹{latest_price:.2f}\n"
            f"{direction}\n\n"
            f"{reason_text}\n\n"
            f"⏰ Time: "
            f"{india_time.strftime('%d-%m-%Y %H:%M:%S')}\n"
            "📡 Source: Yahoo Finance\n\n"
            "⚠️ Informational alert only. "
            "Not investment advice."
        )

        if send_telegram(message):
            alerts_sent += 1

    # ========================================================
    # FINAL LOG
    # ========================================================

    print(
        f"Scan completed. "
        f"Successful: {successful_stocks}, "
        f"Failed: {failed_stocks}, "
        f"Alerts sent: {alerts_sent}"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    if not BOT_TOKEN or not CHAT_ID:

        raise Exception(
            "BOT_TOKEN or CHAT_ID is missing. "
            "Check GitHub Secrets."
        )

    check_market()
