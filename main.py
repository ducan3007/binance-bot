import json
import os
import threading
from pathlib import Path
from typing import List

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from binance_24hr_tickers import binance_24hr_tickers
from logger import logger
from telegram_bot import MessageType1, MessageType2, MessageType3, construct_message, del_message, send_telegram_message

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


STATE_FILE = Path("signal_state.json")
state_lock = threading.Lock()

def read_state_from_file() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            content = f.read()
            if not content:
                return {}
            return json.loads(content)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Could not read or parse state file {STATE_FILE}: {e}. Treating as empty state.")
        return {}


def write_state_to_file(state: dict):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=2)
    except IOError as e:
        logger.error(f"Could not write to state file {STATE_FILE}: {e}")


@app.post("/v2/sendMessage")
def post_send_message_v2(body: MessageType1):
    unique_key = f"{body.symbol}-{body.time_frame}-{body.time}"
    symbol_key = body.symbol.strip("$")

    with state_lock:
        current_state = read_state_from_file()
        last_sent_key = current_state.get(symbol_key)

        if last_sent_key == unique_key:
            logger.warning(f"Duplicate signal blocked. Key: '{unique_key}' for Symbol: {symbol_key}")
            return {
                "status": "Already processed",
                "key": unique_key,
                "message_id": False,
            }

        logger.info(f"New signal received. Processing key: '{unique_key}'")
        try:
            signal = construct_message(body)
            chat_id = BOT[body.time_frame]["chat_id"]
            token = BOT[body.time_frame]["token"]

            response = send_telegram_message(
                signal,
                token=token,
                chat_id=chat_id,
                message=body,
            )

            if response and response.get("message_id"):
                current_state[symbol_key] = unique_key
                write_state_to_file(current_state)
                logger.info(f"Message sent for '{symbol_key}'. State file updated with key: '{unique_key}'.")
                return response
            else:
                logger.error(f"Telegram send failed for key: '{unique_key}'. State NOT updated, allowing retry.")
                return {
                    "status": "failed",
                    "message_id": False,
                }

        except Exception as e:
            logger.error(f"Error processing key '{unique_key}': {e}. State not updated.")
            return {
                "status": "failed",
                "message_id": False,
            }


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
    for id in body.message_id:
        logger.info(f"Deleting message with ID: {id}")
        del_message(token=token, chat_id=chat_id, message_id=id)


def get_images_by_timeframe(time_frame: str) -> List[dict]:
    """Get and sort images from static folder based on time_frame prefix, latest first."""
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

    # Sort by create_time_ns in descending order (latest first)
    images.sort(key=lambda x: x["create_time_ns"], reverse=True)
    return images


@app.get("/chart/{time_frame}", response_class=HTMLResponse)
async def show_images(request: Request, time_frame: str):
    """Endpoint to show images for a given time_frame."""
    images = get_images_by_timeframe(time_frame)

    # Prepare images in triplets for 3-column grid
    image_pairs = [images[i : i + 3] for i in range(0, len(images), 3)]

    return templates.TemplateResponse(
        "index.html", {"request": request, "time_frame": time_frame, "image_pairs": image_pairs}
    )


@app.delete("/delete_image/{filename}")
async def delete_image(filename: str):
    """Endpoint to delete an image from the static folder."""
    static_dir = "static"
    file_path = os.path.join(static_dir, filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return {"message": f"Image {filename} deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Image not found")
