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
    h1 = "1h"
    h2 = "2h"
    h4 = "4h"


class Message(BaseModel):
    signal: str  # BUY or SELL
    symbol: str
    time_frame: TimeFrame
    time: str
    price: float
    change: str


def last_pinned_message_to_file(message_id, symbol, time_frame):
    records = {}

    # Read existing records from the file
    if os.path.exists(PIN_MESSAGE_PATH):
        with open(PIN_MESSAGE_PATH, "r") as file:
            for line in file:
                parts = line.strip().split()
                if len(parts) == 3:
                    existing_symbol, existing_message_id, existing_time_frame = parts
                    records[existing_symbol] = (existing_message_id, existing_time_frame)

    # Update or insert the new record
    records[symbol] = (message_id, time_frame)

    # Write the updated records back to the file
    with open(PIN_MESSAGE_PATH, "w") as file:
        for symbol, (message_id, time_frame) in records.items():
            file.write(f"{symbol} {message_id} {time_frame}\n")


def get_message_id(symbol, time_frame):
    # Check if the file exists
    if not os.path.exists(PIN_MESSAGE_PATH):
        return None

    # Read the records from the file
    with open(PIN_MESSAGE_PATH, "r") as file:
        for line in file:
            parts = line.strip().split()
            if len(parts) == 3:
                existing_symbol, existing_message_id, existing_time_frame = parts
                if existing_symbol == symbol and existing_time_frame == time_frame:
                    return existing_message_id
    return None


def send_telegram_message(signal, token, chat_id, message: Message):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": signal}
    response = requests.post(url, data=payload)
    logger.info(signal)
    logger.info(response.json())
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
                    type="unpinChatMessage",
                )
            return pin_unpin_telegram_message(
                token, chat_id, message_id, message.symbol, message.signal, message.time_frame.value
            )
        else:
            return True
    else:
        logger.info(f"Failed to send message: {message.symbol} {message.signal} {message.time_frame} {message.time}")
        return False


def pin_unpin_telegram_message(
    token,
    chat_id,
    message_id,
    symbol,
    signal,
    time_frame,
    max_retries=5,
    type="pinChatMessage",
):
    url = f"https://api.telegram.org/bot{token}/{type}"
    payload = {"chat_id": chat_id, "message_id": message_id}
    retry_count = 0
    delay = 5  # Initial delay in seconds
    max_delay = 60  # Maximum delay in seconds

    while retry_count < max_retries:
        response = requests.post(url, data=payload)
        logger.info(response.json())
        if response.json()["ok"]:
            logger.info(f"{type} successfully: {symbol} {signal} {time_frame}")
            if type == "pinChatMessage":
                last_pinned_message_to_file(message_id, symbol, time_frame)
            return True
        else:
            logger.info(f"Failed to {type} message: {symbol} {signal} {time_frame}")
            retry_count += 1
            sleep_time = min(delay * (2**retry_count), max_delay)
            logger.info(f"Retrying in {sleep_time} seconds...")
            time.sleep(sleep_time)

    logger.info(f"Failed to {type} message after {max_retries} retries: {symbol} {signal} {time_frame}")
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


def construct_message(message: Message):
    price = format_float_dynamic(message.price)
    return f"\n{message.symbol}\n{Signals[message.signal]}\nPrice   {price} ({message.change})\nTime   {message.time}"
