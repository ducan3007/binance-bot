import os
from fastapi import FastAPI
from telegram_bot import (
    send_telegram_message,
    del_message,
    construct_message,
    MessageType1,
    MessageType2,
    MessageType3
)
from logger import logger
from binance_24hr_tickers import binance_24hr_tickers
from binance_24hr_tickers_v2 import binance_24hr_tickers_v2

CHAT_ID_1M = os.environ.get("CHAT_ID_1M")
TOKEN_1M = os.environ.get("TOKEN_1M")

CHAT_ID_3M = os.environ.get("CHAT_ID_3M")
TOKEN_3M = os.environ.get("TOKEN_3M")

CHAT_ID_5M = os.environ.get("CHAT_ID_5M")
TOKEN_5M = os.environ.get("TOKEN_5M")

CHAT_ID_15M = os.environ.get("CHAT_ID_15M")
TOKEN_15M = os.environ.get("TOKEN_15M")

CHAT_ID_1H = os.environ.get("CHAT_ID_1H")
TOKEN_1H = os.environ.get("TOKEN_1H")

CHAT_ID_2H = os.environ.get("CHAT_ID_2H")
TOKEN_2H = os.environ.get("TOKEN_2H")

CHAT_ID_4H = os.environ.get("CHAT_ID_4H")
TOKEN_4H = os.environ.get("TOKEN_4H")


BOT = {
    "1m": {"chat_id": CHAT_ID_1M, "token": TOKEN_1M},
    "3m": {"chat_id": CHAT_ID_3M, "token": TOKEN_3M},
    "5m": {"chat_id": CHAT_ID_5M, "token": TOKEN_5M},
    "15m": {"chat_id": CHAT_ID_15M, "token": TOKEN_15M},
    "15m_normal": {"chat_id": CHAT_ID_1M, "token": TOKEN_1M},
    "5m_normal": {"chat_id": CHAT_ID_5M, "token": TOKEN_5M},
    "1h": {"chat_id": CHAT_ID_1H, "token": TOKEN_1H},
    "2h": {"chat_id": CHAT_ID_2H, "token": TOKEN_2H},
    "4h": {"chat_id": CHAT_ID_4H, "token": TOKEN_4H},
}

app = FastAPI()


@app.post("/sendMessage")
def post_send_message(body: MessageType1):
    logger.info(f"Received message: {body}")
    signal = construct_message(body)
    chat_id = BOT[body.time_frame]["chat_id"]
    token = BOT[body.time_frame]["token"]
    return send_telegram_message(
        signal,
        token=token,
        chat_id=chat_id,
        message=body,
    )


@app.post("/send24hrPriceChange")
def post_send_24h_price_change(body: MessageType2):
    logger.info(f"Received request to send 24h price change: {body}")
    chat_id = BOT[body.time_frame]["chat_id"]
    token = BOT[body.time_frame]["token"]
    return send_telegram_message(body.message, token=token, chat_id=chat_id, message=body)


@app.post("/trigger-send24hrPriceChange")
def trigger_send_24h_price_change():
    logger.info(f"Triggered 24h price change")
    binance_24hr_tickers()
    logger.info(f"message: Triggered 24h price change V2")
    binance_24hr_tickers_v2()
    logger.info(f"message: Triggered 24h price change")
    return {"message": "Triggered 24h price change"}


@app.post("/deleteMessage")
def delete_message(body: MessageType3):
    logger.info(f"Received request to delete message: {body}")
    chat_id = BOT[body.time_frame]["chat_id"]
    token = BOT[body.time_frame]["token"]
    message_id = body.message_id
    return del_message(token=token, chat_id=chat_id, message_id=message_id)
