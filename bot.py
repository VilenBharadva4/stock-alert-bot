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

RSI_PERIOD = 14
EMA_PERIOD = 20


# ============================================================
# TELEGRAM
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
# GET STOCK DATA
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
                f"{response.status_code}"
            )

            return None

        data = response.json()

        result = data.get("chart", {}).get("result")

        if not result:
            return None

        result = result[0]

        timestamps = result.get("timestamp")

        indicators = result.get("indicators", {})

        quote_data = indicators.get("quote", [])

        if not timestamps or not quote_data:
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

            if i < len(volumes):
                if volumes[i] is not None:
                    volume = volumes[i]

            valid_data.append(
                {
                    "timestamp": timestamps[i],
                    "close": float(close),
                    "volume": float(volume)
                }
            )

        if len(valid_data) < 25:
            print(f"{symbol}: Not enough data.")
            return None

        return valid_data

    except Exception as e:

        print(f"{symbol} error: {e}")

        return None


# ============================================================
# EMA CALCULATION
# ============================================================

def calculate_ema(prices, period):

    if len(prices) < period:
        return None

    multiplier = 2 / (period + 1)

    ema = sum(prices[:period]) / period

    for price in prices[period:]:

        ema = (
            (price - ema) * multiplier
        ) + ema

    return ema


# ============================================================
# RSI CALCULATION
# ============================================================

def calculate_rsi(prices, period=14):

    if len(prices) <= period:
        return None

    gains = []
    losses = []

    for i in range(1, len(prices)):

        change = prices[i] - prices[i - 1]

        if change > 0:

            gains.append(change)
            losses.append(0)

        else:

            gains.append(0)
            losses.append(abs(change))

    average_gain = sum(gains[:period]) / period
    average_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):

        average_gain = (
            (average_gain * (period - 1))
            + gains[i]
        ) / period

        average_loss = (
            (average_loss * (period - 1))
            + losses[i]
        ) / period

    if average_loss == 0:
        return 100.0

    rs = average_gain / average_loss

    rsi = 100 - (100 / (1 + rs))

    return rsi


# ============================================================
# MARKET HOURS
# ============================================================

def is_market_open():

    india_time = datetime.now(
        ZoneInfo("Asia/Kolkata")
    )

    if india_time.weekday() >= 5:
        return False

    current_time = india_time.time()

    market_start = time(9, 15)
    market_end = time(15, 30)

    return (
        market_start
        <= current_time
        <= market_end
    )


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

        # ----------------------------------------------------
        # PRICES
        # ----------------------------------------------------

        prices = [
            item["close"]
            for item in data
        ]

        latest_price = prices[-1]
        previous_price = prices[-2]

        if previous_price <= 0:
            continue

        # ----------------------------------------------------
        # 5-MIN PRICE CHANGE
        # ----------------------------------------------------

        price_change = (
            (latest_price - previous_price)
            / previous_price
        ) * 100

        # ----------------------------------------------------
        # VOLUME
        # ----------------------------------------------------

        recent_volumes = [
            item["volume"]
            for item in data[:-1]
            if item["volume"] > 0
        ]

        recent_volumes = recent_volumes[-10:]

        if recent_volumes:

            average_volume = (
                sum(recent_volumes)
                / len(recent_volumes)
            )

        else:

            average_volume = 0

        latest_volume = data[-1]["volume"]

        volume_ratio = 0

        if average_volume > 0:

            volume_ratio = (
                latest_volume
                / average_volume
            )

        # ----------------------------------------------------
        # RSI
        # ----------------------------------------------------

        rsi = calculate_rsi(
            prices,
            RSI_PERIOD
        )

        # ----------------------------------------------------
        # EMA 20
        # ----------------------------------------------------

        ema20 = calculate_ema(
            prices,
            EMA_PERIOD
        )

        if rsi is None or ema20 is None:
            continue

        # ----------------------------------------------------
        # INDICATOR STATUS
        # ----------------------------------------------------

        if latest_price > ema20:

            ema_status = "🟢 Price above EMA20"

        elif latest_price < ema20:

            ema_status = "🔴 Price below EMA20"

        else:

            ema_status = "⚪ Price near EMA20"

        if rsi >= 70:

            rsi_status = "🔴 RSI Overbought"

        elif rsi <= 30:

            rsi_status = "🟢 RSI Oversold"

        elif rsi >= 50:

            rsi_status = "🟢 RSI Positive Zone"

        else:

            rsi_status = "🟡 RSI Weak Zone"

        # ----------------------------------------------------
        # ALERT CONDITIONS
        # ----------------------------------------------------

        price_alert = (
            abs(price_change)
            >= PRICE_ALERT_PERCENT
        )

        volume_alert = (
            volume_ratio
            >= VOLUME_SPIKE_MULTIPLIER
        )

        rsi_extreme = (
            rsi >= 70
            or rsi <= 30
        )

        # Alert only when meaningful movement exists
        if (
            not price_alert
            and not volume_alert
            and not rsi_extreme
        ):
            continue

        # ----------------------------------------------------
        # DIRECTION
        # ----------------------------------------------------

        if price_change > 0:

            direction = "🟢 UP"

        elif price_change < 0:

            direction = "🔴 DOWN"

        else:

            direction = "⚪ FLAT"

        # ----------------------------------------------------
        # REASONS
        # ----------------------------------------------------

        reasons = []

        if price_alert:

            reasons.append(
                f"📈 5m Price Move: "
                f"{price_change:+.2f}%"
            )

        if volume_alert:

            reasons.append(
                f"📊 Volume Spike: "
                f"{volume_ratio:.1f}x average"
            )

        if rsi_extreme:

            reasons.append(
                f"⚡ RSI: {rsi:.1f}"
            )

        reason_text = "\n".join(reasons)

        # ----------------------------------------------------
        # TELEGRAM MESSAGE
        # ----------------------------------------------------

        message = (
            "🚨 NIFTY 50 MARKET ALERT\n\n"

            f"📌 Stock: {stock_name}\n"
            f"💰 Price: ₹{latest_price:.2f}\n"
            f"{direction}\n\n"

            f"{reason_text}\n\n"

            f"📊 RSI(14): {rsi:.1f}\n"
            f"{rsi_status}\n\n"

            f"📏 EMA(20): ₹{ema20:.2f}\n"
            f"{ema_status}\n\n"

            f"⏰ Time: "
            f"{india_time.strftime('%d-%m-%Y %H:%M:%S')}\n"

            "📡 Data: Yahoo Finance\n\n"

            "⚠️ Informational market alert. "
            "Not investment advice."
        )

        if send_telegram(message):

            alerts_sent += 1

    # --------------------------------------------------------
    # FINAL LOG
    # --------------------------------------------------------

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
