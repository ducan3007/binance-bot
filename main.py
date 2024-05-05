import os
from fastapi import FastAPI
from telegram_bot import send_telegram_message, construct_message, Message
from logger import logger

CHAT_ID_5M = os.environ.get("CHAT_ID_5M")
TOKEN_5M = os.environ.get("TOKEN_5M")


CHAT_ID_15M = os.environ.get("CHAT_ID_15M")
TOKEN_15M = os.environ.get("TOKEN_15M")

BOT = {
    "1m": {"chat_id": "-4213849295", "token": TOKEN_15M},

    "5m": {"chat_id": CHAT_ID_5M, "token": TOKEN_5M},

    "15m": {"chat_id": CHAT_ID_15M, "token": TOKEN_15M},
}

app = FastAPI()


@app.post("/sendMessage")
def post_send_message(message: Message):
    logger.info(f"Received message: {message}")
    signal = construct_message(message)
    chat_id = BOT[message.time_frame]["chat_id"]
    token = BOT[message.time_frame]["token"]
    send_telegram_message(signal, token=token, chat_id=chat_id)
