import time
from enum import Enum
import requests
from logger import logger
from pydantic import BaseModel
import os

Signals = {
    "BUY": "🟢🟢🟢",
    "SELL": "🔻🔻🔻",
}


PIN_MESSAGE_PATH = "pinned_messages.txt"


class TimeFrame(str, Enum):
    m1 = "1m"
    m3 = "3m"
    m5 = "5m"
    m15 = "15m"
    m15_normal = "15m_normal"
    m5_normal = "5m_normal"
    h1 = "1h"
    h2 = "2h"
    h4 = "4h"


class MessageType1(BaseModel):
    signal: str  # BUY or SELL
    symbol: str
    time_frame: TimeFrame
    time: str
    price: float
    change: str


class MessageType2(BaseModel):
    message: str
    time_frame: TimeFrame


def last_pinned_message_to_file(message_id, symbol, time_frame):
    records = []

    # Read existing records from the file
    if os.path.exists(PIN_MESSAGE_PATH):
        with open(PIN_MESSAGE_PATH, "r") as file:
            for line in file:
                parts = line.strip().split()
                if len(parts) == 3:
                    existing_symbol, existing_message_id, existing_time_frame = parts
                    records.append((existing_symbol, existing_message_id, existing_time_frame))

    # Update or insert the new record
    record_updated = False
    for i, (existing_symbol, existing_message_id, existing_time_frame) in enumerate(records):
        if existing_symbol == symbol and existing_time_frame == time_frame:
            records[i] = (symbol, message_id, time_frame)
            record_updated = True
            break

    if not record_updated:
        records.append((symbol, message_id, time_frame))

    # Write the updated records back to the file
    with open(PIN_MESSAGE_PATH, "w") as file:
        for symbol, message_id, time_frame in records:
            file.write(f"{symbol} {message_id} {time_frame}\n")


def get_message_id(symbol, time_frame):
    if not os.path.exists(PIN_MESSAGE_PATH):
        return None

    with open(PIN_MESSAGE_PATH, "r") as file:
        for line in file:
            parts = line.strip().split()
            if len(parts) == 3:
                existing_symbol, existing_message_id, existing_time_frame = parts
                if existing_symbol == symbol and existing_time_frame == time_frame:
                    return existing_message_id
    return None


def handle_message_type1(response, token, chat_id, message: MessageType1):
    if response.json()["ok"] == True:
        logger.info(f"Message sent successfully: {message.symbol} {message.signal} {message.time_frame} {message.time}")
        message_id = response.json()["result"]["message_id"]
        if message.symbol in ["$BTC", "$ETH"] and message.time_frame in [TimeFrame.h2, TimeFrame.m15]:
            last_pinned_message_id = get_message_id(message.symbol, message.time_frame.value)
            if last_pinned_message_id:
                pin_unpin_telegram_message(
                    token,
                    chat_id,
                    last_pinned_message_id,
                    message.symbol,
                    message.signal,
                    message.time_frame,
                    action="unpinChatMessage",
                )
            return pin_unpin_telegram_message(token, chat_id, message_id, message.symbol, message.signal, message.time_frame.value)
        else:
            return True
    else:
        logger.info(f"Failed to send message: {message.symbol} {message.signal} {message.time_frame} {message.time}")
        return False


def handle_message_type2(response, token, chat_id, message: MessageType2):
    symbol = "$DAILY_REPORT"
    signal = "Binace Future Top Gainers & Losers"
    date = time.strftime("%Y-%m-%d", time.localtime())
    if response.json()["ok"] == True:
        logger.info(f"Message sent successfully: {symbol} {signal} {message.time_frame} {date}")
        message_id = response.json()["result"]["message_id"]
        last_pinned_message_id = get_message_id("$DAILY_REPORT", message.time_frame.value)
        if last_pinned_message_id:
            pin_unpin_telegram_message(
                token,
                chat_id,
                last_pinned_message_id,
                symbol,
                signal,
                message.time_frame,
                action="unpinChatMessage",
            )
        return pin_unpin_telegram_message(token, chat_id, message_id, symbol, signal, message.time_frame.value)

    else:
        logger.info(f"Failed to send message: {symbol} {signal} {message.time_frame} {date}")
        return False


def pin_unpin_telegram_message(
    token,
    chat_id,
    message_id,
    symbol,
    signal,
    time_frame,
    max_retries=5,
    action="pinChatMessage",
):
    url = f"https://api.telegram.org/bot{token}/{action}"
    payload = {"chat_id": chat_id, "message_id": message_id}
    retry_count = 0
    delay = 5  # Initial delay in seconds
    max_delay = 41  # Maximum delay in seconds

    while retry_count < max_retries:
        response = requests.post(url, data=payload)
        logger.info(response.json())
        if response.json()["ok"]:
            logger.info(f"{action} successfully: {symbol} {signal} {time_frame}")
            if action == "pinChatMessage":
                last_pinned_message_to_file(message_id, symbol, time_frame)
            return True
        else:
            logger.info(f"Failed to {action} message: {symbol} {signal} {time_frame}")
            retry_count += 1
            sleep_time = min(delay * (2**retry_count), max_delay)
            logger.info(f"Retrying in {sleep_time} seconds...")
            time.sleep(sleep_time)

    logger.info(f"Failed to {action} message after {max_retries} retries: {symbol} {signal} {time_frame}")
    return False


def format_float_dynamic(value):
    """'
    if price > $1, then format to 6 decimal places
    """
    if value >= 1:
        value = round(value, 6)
    s = f"{value:.10f}"
    s = s.rstrip("0").rstrip(".")
    decimals = len(s.split(".")[-1]) if "." in s else 0
    formatted_value = f"{value:.{decimals}f}"
    return formatted_value


def construct_message(message: MessageType1):
    if message.time_frame in [TimeFrame.m5]:
        sub_str = Signals[message.signal][0]
        if message.symbol in ["$BTC", "$ETH"]:
            price = format_float_dynamic(message.price)
            price = "{:,.2f}".format(float(price))
            return f"\n<b>{sub_str} {message.symbol} {message.time}</b>  <code>{message.change}</code>\n<code>{price}</code>"
        return f"\n<b>{sub_str}</b> {message.time} <b>{message.symbol}</b>  <code>{message.change}</code>"
    else:
        sub_str = Signals[message.signal][0]
        if message.symbol in ["$BTC", "$ETH"]:
            price = format_float_dynamic(message.price)
            price = "{:,.2f}".format(float(price))
            return f"\n<b>{sub_str} {message.symbol} {message.time}</b>  <code>{message.change}</code>\n<code>{price}</code>"
        return f"\n<b>{sub_str} {message.symbol} {message.time}</b>  <code>{message.change}</code>"


def send_telegram_message(signal, token, chat_id, message=None):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": signal, "parse_mode": "HTML"}
    response = requests.post(url, data=payload)
    logger.info(signal)
    logger.info(response.json())
    if isinstance(message, MessageType1):
        status = handle_message_type1(response, token, chat_id, message)
        return {
            "status": "success" if status else "failed",
        }
    elif isinstance(message, MessageType2):
        status = handle_message_type2(response, token, chat_id, message)
        return {
            "status": status,
        }
    return {
        "status": response.json()["ok"],
    }
