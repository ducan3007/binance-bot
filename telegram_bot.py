import os
from enum import Enum
import requests
from logger import logger
from pydantic import BaseModel

Signals = {
    "BUY": "🟢🟢🟢",
    "SELL": "🔻🔻🔻",
}


class TimeFrame(str, Enum):
    m1 = "1m"
    m3 = "3m"
    m5 = "5m"
    m15 = "15m"
    h1 = "1h"
    h4 = "4h"


class Message(BaseModel):
    signal: str  # BUY or SELL
    symbol: str
    time_frame: TimeFrame
    time: str
    price: float
    change: str


def send_telegram_message(message, token, chat_id):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    response = requests.post(url, data=payload)
    logger.info(message)
    logger.info(response.json())
    if response.json()["ok"] == True:
        logger.info(f"Message sent successfully ${message}")
        return True
    else:
        logger.info(f"Failed to send message ${message}")
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
