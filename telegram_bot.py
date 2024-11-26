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
    m30 = "30m"
    m30_normal = "30m_normal"
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


class MessageType3(BaseModel):
    time_frame: TimeFrame
    message_id: str


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


def handle_message_type1(url, payload, signal, token, chat_id, message: MessageType1):
    # Unpin the last pinned message first if necessary
    last_pinned_message_id = None
    is_pin = (
        message.symbol in ["$BTC", "$ETH"]
        and message.time_frame in [TimeFrame.h4, TimeFrame.h2, TimeFrame.m30, TimeFrame.h2]
    ) or (message.symbol in ["$BTC"] and message.time_frame in [TimeFrame.m15_normal])
    if is_pin:
        last_pinned_message_id = get_message_id(message.symbol, message.time_frame.value)
        if last_pinned_message_id:
            has_unpinned = pin_unpin_telegram_message(
                token,
                chat_id,
                last_pinned_message_id,
                message.symbol,
                message.signal,
                message.time_frame,
                action="unpinChatMessage",
            )
            if not has_unpinned:
                logger.info(f"Failed to unpin message: {message.symbol} {message.signal} {message.time_frame}")
                return False
        else:
            logger.info(f"No previous message to unpin for: {message.symbol} {message.signal} {message.time_frame}")

    print("IS PIN", is_pin, message.symbol, message.time_frame)
    # Send the new message
    response = requests.post(url, data=payload)
    logger.info(signal)
    logger.info(f"Response type1: {response.json()}")

    if response.json().get("ok"):
        message_id = response.json()["result"]["message_id"]

        # Pin the new message
        if is_pin:
            pin_unpin_telegram_message(
                token, chat_id, message_id, message.symbol, message.signal, message.time_frame.value
            )
            logger.info(f"Pinned new message: {message.symbol} {message.signal} {message.time_frame}")

        logger.info(
            f"Message sent type1 successfully, message_id: {message_id} | {message.symbol} {message.signal} {message.time_frame} {message.time}"
        )
        return message_id
    else:
        logger.info(f"Failed to send message: {message.symbol} {message.signal} {message.time_frame} {message.time}")
        return False


def handle_message_type2(url, payload, signal, token, chat_id, message: MessageType2):
    symbol = "$DAILY_REPORT"
    signal = "Binace Future Top Gainers & Losers"
    date = time.strftime("%Y-%m-%d", time.localtime())

    # Unpin the last pinned message first if necessary
    last_pinned_message_id = get_message_id(symbol, message.time_frame.value)
    if last_pinned_message_id:
        has_unpinned = pin_unpin_telegram_message(
            token,
            chat_id,
            last_pinned_message_id,
            symbol,
            signal,
            message.time_frame,
            action="unpinChatMessage",
        )
        if not has_unpinned:
            logger.info(f"Failed to unpin message: {symbol} {signal} {message.time_frame}")
            return False
    else:
        logger.info(f"No previous message to unpin for: {symbol} {signal} {message.time_frame}")

    # Send the new message
    response = requests.post(url, data=payload)
    if response.json().get("ok"):
        logger.info(f"Message Type 2 sent successfully: {symbol} {signal} {message.time_frame} {date}")
        message_id = response.json()["result"]["message_id"]

        # Pin the new message
        pin_success = pin_unpin_telegram_message(token, chat_id, message_id, symbol, signal, message.time_frame.value)

        if pin_success:
            logger.info(f"New message pinned: {symbol} {signal} {message.time_frame}")
            return True
        else:
            logger.info(f"Failed to pin new message: {symbol} {signal} {message.time_frame}")
            return False

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
    action="pinChatMessage",
):
    url = f"https://api.telegram.org/bot{token}/{action}"
    payload = {"chat_id": chat_id, "message_id": message_id}

    response = requests.post(url, data=payload)
    response_data = response.json()
    logger.info(response_data)

    if response_data["ok"]:
        logger.info(f"{action} successfully: {symbol} {signal} {time_frame}")
        if action == "pinChatMessage":
            last_pinned_message_to_file(message_id, symbol, time_frame)
        elif action == "unpinChatMessage":
            last_pinned_message_to_file("", symbol, time_frame)
            return True
    else:
        logger.info(f"Failed to {action} message: {symbol} {signal} {time_frame}")
        if response_data["error_code"] == 400:
            last_pinned_message_to_file("", symbol, time_frame)
            return True
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
    sub_str = Signals[message.signal][0]
    is_show_price = (message.symbol in ["$BTC", "$ETH", "$SOL"] and message.time_frame not in [TimeFrame.m5, TimeFrame.m3]) or (
        message.symbol in ["$BTC", "$ETH", "$SOL"] and message.time_frame in [TimeFrame.m5]
    )
    if message.symbol in ["$BTC", "$ETH", "$SOL", "$BNB", "$PEPE", "$XRP", "$SUI", "$DOGE"] and message.time_frame not in [TimeFrame.m3]:
        msg = message.symbol + "*"
    else:
        msg = message.symbol

    if is_show_price:
        price = format_float_dynamic(message.price)
        price = "{:,.2f}".format(float(price))
        return (
            f"<b>{sub_str}</b> <b>{message.time}</b>  <b>{msg}</b> <code>{price}</code> <code>{message.change}</code>"
        )
    return f"<b>{sub_str}</b> <b>{message.time}</b>  <b>{msg}</b> <code>{message.change}</code>"


def send_telegram_message(signal, token, chat_id, message=None):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": signal, "parse_mode": "HTML"}
    if isinstance(message, MessageType1):
        ack = handle_message_type1(url, payload, signal, token, chat_id, message)
        return {
            "status": "success" if ack else "failed",
            "message_id": ack,
        }
    elif isinstance(message, MessageType2):
        ack = handle_message_type2(url, payload, signal, token, chat_id, message)
        return {
            "status": ack,
        }


def del_message(token, chat_id, message_id):
    url = f"https://api.telegram.org/bot{token}/deleteMessage"
    payload = {"chat_id": chat_id, "message_id": message_id}

    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()  # Raises an error for bad HTTP status codes
        response_data = response.json()

        if response_data.get("ok") and response_data.get("result"):
            logger.info(f"Message {message_id} deleted successfully.")
            return {
                "status": True,
                "message": "Message deleted successfully",
            }
        else:
            logger.info(f"Failed to delete message: {response_data}")
            return {
                "status": False,
                "message": "Failed to delete message",
            }
    except requests.exceptions.RequestException as e:
        if e.response is not None and e.response.status_code == 400:
            logger.info(f"Message not found: {message_id}")
            return {
                "status": True,
                "message": "Message not found",
            }
        else:
            logger.info(f"Failed to delete message: {e}")
            return {
                "status": False,
                "message": "Request failed",
            }
