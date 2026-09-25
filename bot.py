import os
import json
import base64
import requests

from datetime import datetime, time, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo


# ============================================================
# SETTINGS
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPOSITORY = os.getenv("GITHUB_REPOSITORY")

STATE_FILE = "trade_state.json"


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
# TRADE SETTINGS
# ============================================================

ENTRY_RSI_MIN = 50
ENTRY_RSI_MAX = 68

ENTRY_VOLUME_MULTIPLIER = 1.5

TARGET_PERCENT = 1.0
STOP_PERCENT = 0.7

MAX_HOLD_MINUTES = 30

EMA_PERIOD = 20
RSI_PERIOD = 14


# ============================================================
# TELEGRAM
# ============================================================

def send_telegram(message):

    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram credentials missing.")
        return False

    url = (
        f"https://api.telegram.org/"
        f"bot{BOT_TOKEN}/sendMessage"
    )

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
            f"{response.status_code} "
            f"{response.text[:300]}"
        )

    except Exception as e:

        print(f"Telegram connection error: {e}")

    return False


# ============================================================
# GITHUB STATE FUNCTIONS
# ============================================================

def load_state():

    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:
        print("GitHub state storage not configured.")
        return {}

    url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_REPOSITORY}/contents/{STATE_FILE}"
    )

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        if response.status_code == 404:

            print("No previous trade state found.")

            return {}

        if response.status_code != 200:

            print(
                f"State load error: "
                f"{response.status_code}"
            )

            return {}

        data = response.json()

        content = data.get("content", "")

        decoded = base64.b64decode(
            content
        ).decode("utf-8")

        return json.loads(decoded)

    except Exception as e:

        print(f"State load error: {e}")

        return {}


def save_state(state):

    if not GITHUB_TOKEN or not GITHUB_REPOSITORY:

        print("GitHub state storage unavailable.")

        return False

    url = (
        f"https://api.github.com/repos/"
        f"{GITHUB_REPOSITORY}/contents/{STATE_FILE}"
    )

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    try:

        # Check existing file
        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        sha = None

        if response.status_code == 200:

            sha = response.json().get("sha")

        content = json.dumps(
            state,
            indent=2
        )

        encoded = base64.b64encode(
            content.encode("utf-8")
        ).decode("utf-8")

        payload = {
            "message": "Update trade state",
            "content": encoded
        }

        if sha:
            payload["sha"] = sha

        response = requests.put(
            url,
            headers=headers,
            json=payload,
            timeout=15
        )

        if response.status_code in [200, 201]:

            print("Trade state saved.")

            return True

        print(
            f"State save error: "
            f"{response.status_code} "
            f"{response.text[:300]}"
        )

    except Exception as e:

        print(f"State save error: {e}")

    return False


# ============================================================
# YAHOO FINANCE DATA
# ============================================================

def get_stock_data(symbol):

    try:

        encoded_symbol = quote(
            symbol,
            safe=""
        )

        url = (
            "https://query1.finance.yahoo.com/"
            "v8/finance/chart/"
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

        result = (
            data
            .get("chart", {})
            .get("result")
        )

        if not result:
            return None

        result = result[0]

        timestamps = result.get("timestamp")

        indicators = result.get(
            "indicators",
            {}
        )

        quote_data = indicators.get(
            "quote",
            []
        )

        if not timestamps or not quote_data:
            return None

        quote_data = quote_data[0]

        closes = quote_data.get(
            "close",
            []
        )

        volumes = quote_data.get(
            "volume",
            []
        )

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

            return None

        return valid_data

    except Exception as e:

        print(
            f"{symbol} error: {e}"
        )

        return None


# ============================================================
# EMA
# ============================================================

def calculate_ema(
    prices,
    period
):

    if len(prices) < period:
        return None

    multiplier = (
        2 / (period + 1)
    )

    ema = (
        sum(prices[:period])
        / period
    )

    for price in prices[period:]:

        ema = (
            (price - ema)
            * multiplier
        ) + ema

    return ema


# ============================================================
# RSI
# ============================================================

def calculate_rsi(
    prices,
    period=14
):

    if len(prices) <= period:
        return None

    gains = []
    losses = []

    for i in range(
        1,
        len(prices)
    ):

        change = (
            prices[i]
            - prices[i - 1]
        )

        if change > 0:

            gains.append(change)
            losses.append(0)

        else:

            gains.append(0)
            losses.append(
                abs(change)
            )

    average_gain = (
        sum(gains[:period])
        / period
    )

    average_loss = (
        sum(losses[:period])
        / period
    )

    for i in range(
        period,
        len(gains)
    ):

        average_gain = (
            (
                average_gain
                * (period - 1)
            )
            + gains[i]
        ) / period

        average_loss = (
            (
                average_loss
                * (period - 1)
            )
            + losses[i]
        ) / period

    if average_loss == 0:

        return 100.0

    rs = (
        average_gain
        / average_loss
    )

    return (
        100
        - (100 / (1 + rs))
    )


# ============================================================
# MARKET HOURS
# ============================================================

def is_market_open():

    india_time = datetime.now(
        ZoneInfo("Asia/Kolkata")
    )

    if india_time.weekday() >= 5:
        return False

    current_time = (
        india_time.time()
    )

    return (
        time(9, 15)
        <= current_time
        <= time(15, 30)
    )


# ============================================================
# SCAN ONE STOCK
# ============================================================

def get_indicators(data):

    prices = [
        x["close"]
        for x in data
    ]

    latest_price = prices[-1]
    previous_price = prices[-2]

    price_change = (
        (
            latest_price
            - previous_price
        )
        / previous_price
    ) * 100

    volumes = [
        x["volume"]
        for x in data[:-1]
        if x["volume"] > 0
    ]

    volumes = volumes[-10:]

    if volumes:

        average_volume = (
            sum(volumes)
            / len(volumes)
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

    rsi = calculate_rsi(
        prices,
        RSI_PERIOD
    )

    ema20 = calculate_ema(
        prices,
        EMA_PERIOD
    )

    return {
        "price": latest_price,
        "price_change": price_change,
        "volume_ratio": volume_ratio,
        "rsi": rsi,
        "ema20": ema20
    }


# ============================================================
# ENTRY CONDITION
# ============================================================

def is_entry_signal(indicators):

    price = indicators["price"]
    change = indicators["price_change"]
    volume = indicators["volume_ratio"]
    rsi = indicators["rsi"]
    ema20 = indicators["ema20"]

    if rsi is None or ema20 is None:
        return False

    return (
        price > ema20
        and ENTRY_RSI_MIN <= rsi <= ENTRY_RSI_MAX
        and change > 0
        and volume >= ENTRY_VOLUME_MULTIPLIER
    )


# ============================================================
# CREATE ENTRY
# ============================================================

def create_entry(
    stock_name,
    indicators,
    india_time
):

    entry_price = indicators["price"]

    target_price = (
        entry_price
        * (1 + TARGET_PERCENT / 100)
    )

    stop_price = (
        entry_price
        * (1 - STOP_PERCENT / 100)
    )

    return {
        "stock": stock_name,
        "entry_price": entry_price,
        "target_price": target_price,
        "stop_price": stop_price,
        "entry_time": india_time.isoformat()
    }


# ============================================================
# EXIT CHECK
# ============================================================

def check_exit(
    trade,
    current_price,
    current_time
):

    entry_price = trade["entry_price"]
    target_price = trade["target_price"]
    stop_price = trade["stop_price"]

    entry_time = datetime.fromisoformat(
        trade["entry_time"]
    )

    # TARGET
    if current_price >= target_price:

        return (
            "TARGET",
            f"Price reached target ₹{target_price:.2f}"
        )

    # STOP
    if current_price <= stop_price:

        return (
            "STOP",
            f"Price reached stop ₹{stop_price:.2f}"
        )

    # MAX HOLD TIME
    elapsed = (
        current_time
        - entry_time
    )

    if elapsed >= timedelta(
        minutes=MAX_HOLD_MINUTES
    ):

        return (
            "TIME",
            f"Maximum hold time "
            f"{MAX_HOLD_MINUTES} minutes reached"
        )

    return None, None


# ============================================================
# MAIN MARKET SCANNER
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

    state = load_state()

    active_trades = state.get(
        "active_trades",
        {}
    )

    successful = 0
    failed = 0
    entries = 0
    exits = 0

    for stock_name, symbol in WATCHLIST.items():

        data = get_stock_data(symbol)

        if not data:

            failed += 1

            continue

        successful += 1

        indicators = get_indicators(data)

        current_price = indicators["price"]

        # ====================================================
        # ACTIVE TRADE
        # ====================================================

        if stock_name in active_trades:

            trade = active_trades[
                stock_name
            ]

            exit_type, exit_reason = (
                check_exit(
                    trade,
                    current_price,
                    india_time
                )
            )

            if exit_type:

                entry_price = (
                    trade["entry_price"]
                )

                profit_percent = (
                    (
                        current_price
                        - entry_price
                    )
                    / entry_price
                ) * 100

                if profit_percent >= 0:

                    result_icon = "🟢"

                else:

                    result_icon = "🔴"

                message = (
                    "🚪 EXIT SIGNAL\n\n"

                    f"📌 Stock: {stock_name}\n"
                    f"💰 Entry: ₹{entry_price:.2f}\n"
                    f"💰 Exit: ₹{current_price:.2f}\n\n"

                    f"{result_icon} "
                    f"Move: {profit_percent:+.2f}%\n\n"

                    f"📍 Reason: {exit_reason}\n"
                    f"⏰ Exit: "
                    f"{india_time.strftime('%H:%M:%S')}\n\n"

                    "⚠️ Rule-based informational signal. "
                    "Not guaranteed."
                )

                if send_telegram(message):

                    exits += 1

                    del active_trades[
                        stock_name
                    ]

            else:

                print(
                    f"{stock_name}: "
                    f"Active trade | "
                    f"₹{current_price:.2f}"
                )

            continue

        # ====================================================
        # NEW ENTRY
        # ====================================================

        if is_entry_signal(indicators):

            trade = create_entry(
                stock_name,
                indicators,
                india_time
            )

            active_trades[
                stock_name
            ] = trade

            message = (
                "🟢 ENTRY SIGNAL\n\n"

                f"📌 Stock: {stock_name}\n"
                f"💰 Entry Price: "
                f"₹{trade['entry_price']:.2f}\n\n"

                f"🎯 Target: "
                f"₹{trade['target_price']:.2f}\n"

                f"🛑 Stop: "
                f"₹{trade['stop_price']:.2f}\n\n"

                f"📊 RSI(14): "
                f"{indicators['rsi']:.1f}\n"

                f"📏 EMA20: "
                f"₹{indicators['ema20']:.2f}\n"

                f"📈 5M Move: "
                f"{indicators['price_change']:+.2f}%\n"

                f"📊 Volume: "
                f"{indicators['volume_ratio']:.1f}x average\n\n"

                f"⏳ Max Hold: "
                f"{MAX_HOLD_MINUTES} minutes\n"

                f"⏰ Entry Time: "
                f"{india_time.strftime('%H:%M:%S')}\n\n"

                "⚠️ Rule-based informational signal. "
                "Not guaranteed."
            )

            if send_telegram(message):

                entries += 1

    # ========================================================
    # SAVE STATE
    # ========================================================

    state["active_trades"] = active_trades

    save_state(state)

    print(
        f"Scan completed. "
        f"Successful: {successful}, "
        f"Failed: {failed}, "
        f"New entries: {entries}, "
        f"Exits: {exits}, "
        f"Active trades: "
        f"{len(active_trades)}"
    )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    if not BOT_TOKEN or not CHAT_ID:

        raise Exception(
            "BOT_TOKEN or CHAT_ID is missing."
        )

    check_market()
