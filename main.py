import os
from fastapi import FastAPI, Request
from telegram_bot import send_telegram_message, del_message, construct_message, MessageType1, MessageType2, MessageType3
from logger import logger
from binance_24hr_tickers import binance_24hr_tickers
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import List

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

CHAT_ID_15M_V2 = os.environ.get("CHAT_ID_15M_V2")
TOKEN_15M_V2 = os.environ.get("TOKEN_15M_V2")

CHAT_ID_TOP = os.environ.get("CHAT_ID_TOP")
TOKEN_TOP = os.environ.get("TOKEN_TOP")

BOT = {
    "1m": {"chat_id": CHAT_ID_1M, "token": TOKEN_1M},
    "3m": {"chat_id": CHAT_ID_TOP, "token": TOKEN_TOP},
    "5m": {"chat_id": CHAT_ID_15M_V2, "token": TOKEN_15M_V2},
    "15m_v2": {"chat_id": CHAT_ID_15M_V2, "token": TOKEN_15M_V2},
    "15m": {"chat_id": CHAT_ID_15M, "token": TOKEN_15M},
    "30m": {"chat_id": CHAT_ID_15M_V2, "token": TOKEN_15M_V2},
    "30m_normal": {"chat_id": CHAT_ID_15M, "token": TOKEN_15M},
    "15m_normal": {"chat_id": CHAT_ID_15M, "token": TOKEN_15M},
    "5m_normal": {"chat_id": CHAT_ID_1M, "token": TOKEN_1M},
    "1h": {"chat_id": CHAT_ID_2H, "token": TOKEN_2H},
    "1h_normal": {"chat_id": CHAT_ID_2H, "token": TOKEN_2H},
    "2h": {"chat_id": CHAT_ID_2H, "token": TOKEN_2H},
    "4h": {"chat_id": CHAT_ID_2H, "token": TOKEN_2H},
}

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

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

@app.post("/deleteMessage")
def delete_message(body: MessageType3):
    logger.info(f"Received request to delete message: {body}")
    chat_id = BOT[body.time_frame]["chat_id"]
    token = BOT[body.time_frame]["token"]
    message_id = body.message_id
    return del_message(token=token, chat_id=chat_id, message_id=message_id)

def get_images_by_timeframe(time_frame: str) -> List[dict]:
    """Get and sort images from static folder based on time_frame prefix."""
    static_dir = "static"
    images = []

    if not os.path.exists(static_dir):
        return images

    # List all files in static directory
    for filename in os.listdir(static_dir):
        if filename.startswith(f"{time_frame}_") and filename.endswith(".png"):
            # Split filename to extract components
            parts = filename.split("_")
            if len(parts) == 5:  # Ensure correct format
                tf, title, signal, time1, create_time = parts
                try:
                    create_time_ns = float(create_time.replace(".png", ""))
                    images.append(
                        {
                            "filename": filename,
                            "title": title,
                            "signal": signal,
                            "time1": time1,
                            "create_time_ns": create_time_ns,
                        }
                    )
                except ValueError:
                    # Skip files where create_time isn't a valid float
                    continue

    # Sort by create_time_ns
    images.sort(key=lambda x: x["create_time_ns"])
    return images

@app.get("/chart/{time_frame}", response_class=HTMLResponse)
async def show_images(request: Request, time_frame: str):
    """Endpoint to show images for a given time_frame."""
    images = get_images_by_timeframe(time_frame)

    # Prepare images in pairs for 2-column grid
    image_pairs = [images[i:i + 2] for i in range(0, len(images), 2)]

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "time_frame": time_frame, "image_pairs": image_pairs}
    )