import os
from enum import Enum
import requests
from logger import logger
from pydantic import BaseModel

Signals = {
    "BUY": " 🟢 ",
    "SELL": " 🔴 ",
}


class TimeFrame(str, Enum):
    m1 = "1m"
    m5 = "5m"
    m15 = "15m"


class Message(BaseModel):
    signal: str  # BUY or SELL
    symbol: str
    time_frame: TimeFrame
    price: float


def send_telegram_message(message, token, chat_id):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message}
    response = requests.post(url, data=payload)
    logger.info(message)
    logger.info(response.json())


def contruct_message(message: Message):
    return f"[TESTING] {message.symbol}  {Signals[message.signal]}\nPrice: {message.price}"
