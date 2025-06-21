import argparse
import json
import multiprocessing
import os
import random
import time
import traceback
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Literal

import pandas as pd
import requests
from binance.spot import Spot

import chart
from lib.trend import ema_indicator
from logger import logger

# --- Constants ---

EPSILON = 1e-9

NON_SPOT_PAIRS = {
    "TONUSDT",
    "ONDOUSDT",
    "1000PEPEUSDT",
    "1000BONKUSDT",
    "1000RATSUSDT",
    "1000FLOKIUSDT",
    "1000SHIBUSDT",
    "MEWUSDT",
    "ZETAUSDT",
}

TOKEN_SHORTCUT = {
    "1000PEPE": "PEPE",
    "1000BONK": "BONK",
    "1000RATS": "RATS",
    "1000SATS": "SATS",
    "1000FLOKI": "FLOKI",
    "1000SHIB": "SHIB",
    "1MBABYDOGE": "BABYDOGE",
    "BTCDOM": "BTCD",
}

TIME_FRAME_SECONDS = {
    "3m": 3 * 60,
    "5m": 5 * 60,
    "15m": 15 * 60,
    "30m": 30 * 60,
    "1h": 60 * 60,
}

TELEGRAM_API_BASE_URL = "http://localhost:8000"
BINANCE_FUTURE_API_URL = "https://fapi.binance.com/fapi/v1/klines"


# --- Data Structure Initialization ---


def init_kline_data_dict() -> Dict[str, List[Any]]:
    keys = [
        "Open",
        "High",
        "Low",
        "Close",
        "Time1",
        "Time",
        "Open_p",
        "Close_p",
    ]
    return {key: [] for key in keys}


# --- Helper Classes ---


class KlineHelper:
    def __init__(self, mode: str, exchange: str):
        print(f"KlineHelper: mode={mode}, exchange={exchange}")
        self.mode = mode
        self.exchange = exchange
        self.weight = {"m1": 0}

    def _append_candle_base(self, data: Dict, kline: List) -> None:
        data["Time1"].append(datetime.fromtimestamp(int(kline[0]) / 1000).strftime("%Y-%m-%d %H:%M"))
        data["Time"].append(int(kline[0]) / 1000)
        data["Open_p"].append(float(kline[1]))
        data["Close_p"].append(float(kline[4]))

    def _append_kline(self, data: Dict, kline: List) -> None:
        data["Open"].append(float(kline[1]))
        data["High"].append(float(kline[2]))
        data["Low"].append(float(kline[3]))
        data["Close"].append(float(kline[4]))
        self._append_candle_base(data, kline)

    def _append_heikin_ashi(self, data: Dict, kline: List, prev_item: Dict = None) -> None:
        open_p, high_p, low_p, close_p = map(float, kline[1:5])

        if len(data["Close"]) > 0:
            ha_open = (data["Open"][-1] + data["Close"][-1]) / 2
        elif prev_item:
            ha_open = (prev_item["Open"] + prev_item["Close"]) / 2
        else:
            ha_open = open_p

        ha_close = (open_p + high_p + low_p + close_p) / 4
        ha_high = max(high_p, ha_open, ha_close)
        ha_low = min(low_p, ha_open, ha_close)

        data["Open"].append(ha_open)
        data["High"].append(ha_high)
        data["Low"].append(ha_low)
        data["Close"].append(ha_close)
        self._append_candle_base(data, kline)

    def populate(self, data: Dict, klines: List, prev_item: Dict = None) -> None:
        for kline in klines:
            if self.mode == "heikin_ashi":
                self._append_heikin_ashi(data, kline, prev_item)
            else:
                self._append_kline(data, kline)

    def _pop_tail_data(self, data: Dict) -> None:
        for key in data:
            if data[key]:
                data[key].pop()

    def _pop_top_data(self, data: Dict) -> None:
        for key in data:
            if data[key]:
                data[key].pop(0)

    def _fetch_klines_future(self, pair: str, time_frame: str, limit: int) -> List:
        try:
            url = f"{BINANCE_FUTURE_API_URL}?symbol={pair}&interval={time_frame}&limit={limit}"
            headers = {"Content-Type": "application/json"}
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            self.weight["m1"] = int(res.headers.get("x-mbx-used-weight-1m", 0))
            return res.json()
        except requests.RequestException as e:
            logger.error(f"Error Fetching Future Klines for {pair}: {e}")
            raise

    def fetch_klines(self, binance_spot: Spot, pair: str, time_frame: str, limit: int) -> List:
        use_future_api = self.exchange == "future" or pair in NON_SPOT_PAIRS
        if use_future_api:
            return self._fetch_klines_future(pair, time_frame, limit)
        return binance_spot.klines(pair, time_frame, limit=limit)


class EMA:
    def __init__(self, pair: str, time_frame: str, mode: str, exchange: str, size: int = 1000):
        print(f"EMA: {pair} {time_frame} {mode} {exchange} {size}")
        self.pair = pair
        self.time_frame = time_frame
        self.size = size
        self.binance_spot = Spot()
        self.kline_helper = KlineHelper(mode=mode, exchange=exchange)
        self.data: Dict[str, List[Any]] = init_kline_data_dict()
        self.df: pd.DataFrame = pd.DataFrame()
        self.timestamp: float = 0.0
        self.ema_200_value: float = None
        self.ema_35_value: float = None
        self.ema_21_value: float = None

    def fetch_klines(self) -> None:
        logger.info(f"Fetching initial EMA klines for {self.pair}")
        self.data = init_kline_data_dict()
        klines = self.kline_helper.fetch_klines(self.binance_spot, self.pair, self.time_frame, self.size)
        self.kline_helper.populate(self.data, klines)
        self.df = pd.DataFrame(self.data)
        self.timestamp = self.data["Time"][-1]

    def update_klines(self, latest_klines: List) -> None:
        new_data = init_kline_data_dict()
        if not latest_klines:
            latest_klines = self.kline_helper.fetch_klines(self.binance_spot, self.pair, self.time_frame, 2)

        self.kline_helper.populate(new_data, latest_klines)

        latest_new_timestamp = new_data["Time"][-1]
        last_existing_timestamp = self.data["Time"][-1] if self.data["Time"] else 0

        expected_next_timestamp = last_existing_timestamp + TIME_FRAME_SECONDS.get(self.time_frame, 0)

        if latest_new_timestamp == last_existing_timestamp:
            self.kline_helper._pop_tail_data(self.data)
            self.kline_helper.populate(self.data, [latest_klines[-1]])
        elif latest_new_timestamp == expected_next_timestamp:
            self.kline_helper._pop_top_data(self.data)
            self.kline_helper.populate(self.data, [latest_klines[-1]])
        else:
            logger.error(
                f"Timestamp mismatch for {self.pair}: Last: {last_existing_timestamp}, New: {latest_new_timestamp}. Resyncing."
            )
            self.fetch_klines()

        self.df = pd.DataFrame(self.data)
        self.timestamp = self.df["Time"].iloc[-1]

    def calculate_all_emas(self) -> None:
        self.df["EMA_200"] = ema_indicator(self.df["Close"], 200)
        self.ema_200_value = self.df["EMA_200"].iloc[-1]

        self.df["EMA_35"] = ema_indicator(self.df["Close"], 34)
        self.ema_35_value = self.df["EMA_35"].iloc[-1]

        self.df["EMA_21"] = ema_indicator(self.df["Close"], 21)
        self.ema_21_value = self.df["EMA_21"].iloc[-1]

    def check_cross(
        self, time_frame: str, open_p: float, high: float, low: float, close: float, signal: Literal["BUY", "SELL"]
    ) -> Dict[str, bool]:
        res = {"ema_200_cross": False, "ema_35_cross": False, "ema_21_cross": False}

        if any(v is None for v in [self.ema_200_value, self.ema_35_value, self.ema_21_value]):
            logger.info(f"EMA values are not yet calculated for {self.pair}, calculating now.")
            self.calculate_all_emas()
            if any(v is None for v in [self.ema_200_value, self.ema_35_value, self.ema_21_value]):
                logger.error(f"EMA values are still None after calculation for {self.pair}.")
                return res

        is_greater = lambda a, b: (a - b) > EPSILON
        is_less = lambda a, b: (b - a) > EPSILON

        emas_to_check = {
            "ema_200_cross": self.ema_200_value,
            "ema_35_cross": self.ema_35_value,
            "ema_21_cross": self.ema_21_value,
        }

        use_close_for_cross = time_frame in ["5m", "15m"]

        for key, ema_value in emas_to_check.items():
            if signal == "BUY":
                cross_point = close if use_close_for_cross else high
                if is_less(open_p, ema_value) and is_greater(cross_point, ema_value):
                    res[key] = True
            elif signal == "SELL":
                cross_point = close if use_close_for_cross else low
                if is_greater(open_p, ema_value) and is_less(cross_point, ema_value):
                    res[key] = True
        return res


# --- Utility Functions ---


def remove_file(filename) -> None:
    try:
        if isinstance(filename, list):
            for fname in filename:
                if os.path.exists(fname):
                    os.remove(fname)
        elif os.path.exists(filename):
            if os.path.exists(filename):
                os.remove(filename)
    except OSError:
        pass


def format_price_change(current: float, previous: float) -> str:
    if previous == 0:
        return "0.00%"
    percent_change = (current - previous) / previous * 100
    return f"+{percent_change:.2f}%" if percent_change >= 0 else f"{percent_change:.2f}%"


def send_telegram_api_request(endpoint: str, body: Dict) -> Dict:
    try:
        url = f"{TELEGRAM_API_BASE_URL}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to send request to {endpoint}: {e}")
        return {"status": "error", "message": str(e)}


def send_telegram_message(body: Dict) -> Dict:
    res = send_telegram_api_request("sendMessage", body)
    return res if res.get("status") == "success" else None


# --- Core Strategy Logic ---

def main(
    data: Dict, token: str, time_frame: str, pair: str, version: str, time_sleep: int, mode: str, exchange: str
) -> None:
    # --- Initialization ---
    logger.info(f"Starting {pair}: MODE: {mode}, Signal TF: 1h, EMA TF: 1h")

    kline_helper = KlineHelper(mode=mode, exchange=exchange)
    binance_spot = Spot()

    ema_handler = EMA(pair=pair, time_frame="1h", mode="normal", exchange=exchange, size=1000)
    ema_handler.fetch_klines()

    # --- Correct State Management ---
    # This variable tracks the integer hour (0-23) for which a signal has been sent.
    # We initialize to -1 to ensure the first check runs.
    last_signaled_hour = -1

    short_token = TOKEN_SHORTCUT.get(token, token)
    token_for_log = token.ljust(12)

    # --- Main Loop ---
    while True:
        now = datetime.utcnow()

        # --- High-Level State Check ---
        # If the current hour is the same as the one we last signaled for,
        # we do nothing and wait for the next hour.
        if now.hour == last_signaled_hour:
            print(
                f"Time: {now.strftime('%H:%M:%S')} W:{kline_helper.weight['m1']} {token_for_log} Signal already sent for hour {now.hour:02d}. Waiting..."
            )
            time.sleep(time_sleep)
            continue # Skip to the next loop iteration

        # If a new hour has started, we reset our state to allow a new signal.
        # This is implicitly handled by `last_signaled_hour` not matching `now.hour`.
        print(
            f"Time: {now.strftime('%H:%M:%S')} W:{kline_helper.weight['m1']} {token_for_log} Waiting for {now.hour:02d}:55..."
        )

        # Only proceed to check for signals in the last 5 minutes of the hour.
        if now.minute >= 55:
            try:
                latest_klines = kline_helper.fetch_klines(binance_spot, pair, "1h", 2)

                if not latest_klines or len(latest_klines) < 2:
                    logger.warning(f"Not enough 1h kline data for {pair} to determine signal.")
                    time.sleep(time_sleep)
                    continue

                # The rest of the logic is the same as before
                prev_closed_candle = latest_klines[-2]
                prev_close_price = float(prev_closed_candle[4])

                current_candle = latest_klines[-1]
                open_time = int(current_candle[0])
                open_price = float(current_candle[1])
                high_price = float(current_candle[2])
                low_price = float(current_candle[3])
                current_price = float(current_candle[4])

                signal = None
                if (current_price - open_price) > EPSILON:
                    signal = "BUY"
                elif (open_price - current_price) > EPSILON:
                    signal = "SELL"

                if signal:
                    logger.info(f"Signal condition met for {pair}: {signal} (O:{open_price}, C:{current_price})")

                    ema_handler.update_klines(None)
                    ema_handler.calculate_all_emas()
                    ema_cross = ema_handler.check_cross(
                        time_frame, open_price, high_price, low_price, current_price, signal
                    )

                    percent_change = format_price_change(current_price, prev_close_price)
                    signal_time = datetime.fromtimestamp(open_time / 1000 + 3600).strftime("%H:%M")

                    time.sleep(random.uniform(1.0, 5.0))
                    image_path = chart.get_charts(
                        f"{short_token}", PAIR=pair, TIME_FRAME=time_frame, signal=signal, time1=signal_time
                    )

                    body = {
                        "signal": signal,
                        "symbol": f"${short_token}",
                        "time_frame": "5m",
                        "time": signal_time,
                        "price": current_price,
                        "change": percent_change,
                        "ema_cross": ema_cross,
                        "image": image_path,
                    }

                    res = send_telegram_message(body)
                    if res and res.get("message_id"):
                        # --- CRITICAL: Update state upon successful send ---
                        last_signaled_hour = now.hour
                        logger.info(f"Signal sent for {pair} for hour {now.hour}. Locking until next hour. | message_id: {res.get('message_id')}")
                    else:
                        logger.error(f"Failed to send signal for {pair}: {body}")
                        remove_file(image_path)

            except Exception:
                logger.error(f"[{token}] Error in signal generation loop: {traceback.format_exc()}")

        time.sleep(time_sleep)
        
def run_strategy(token: str, time_frame: str, pair: str, version: str, time_sleep: int, mode: str, exchange: str):
    while True:
        try:
            logger.info(f"Starting strategy for {mode} {token} {time_frame} {pair}")
            data = init_kline_data_dict()
            main(data, token, time_frame, pair, version, time_sleep, mode, exchange)
        except Exception:
            logger.error(f"[{token}] Unhandled exception in strategy: {traceback.format_exc()}")
            time.sleep(5)
        finally:
            logger.info(f"[{token}] Restarting strategy process...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a trading bot strategy based on 1-hour candle color.")
    parser.add_argument("--timeframe", type=str, help="EMA Time frame (e.g., '5m', '1h')", default="5m")
    parser.add_argument("--sleep", type=int, help="Sleep time in seconds between loops", default=20)
    parser.add_argument("--mode", type=str, help="Chart mode: 'heikin_ashi' or 'normal'", default="heikin_ashi")
    parser.add_argument("--exchange", type=str, help="Exchange: 'future' or 'spot'", default="future")
    parser.add_argument("--version", type=str, help="Strategy version suffix for identification", default="")
    args = parser.parse_args()

    token_list_files = {
        "1m": "tokens.1m.txt",
        "3m": "tokens.top.txt",
        "5m": "tokens.5m.txt",
        "5mheikin_ashi": "tokens.5m.txt",
        "15m": "tokens.15m.txt",
        "15mv2": "tokens.top.txt",
        "15mnormal": "tokens.15m.txt",
        "5mnormal": "tokens.15m.normal.txt",
        "30mnormal": "tokens.30m.txt",
        "30m": "tokens.top.txt",
        "1h": "tokens.txt",
        "1hnormal": "tokens.txt",
        "2h": "tokens.txt",
        "4h": "tokens.txt",
    }

    file_key = f"{args.timeframe}{args.mode}{args.version}"
    token_file = token_list_files.get(file_key)

    if not token_file or not os.path.exists(token_file):
        logger.error(f"Could not find a valid token file for key '{file_key}'. Exiting.")
        exit(1)

    with open(token_file, "r") as file:
        tokens = [line.strip() for line in file if line.strip()]

    strategies = [(token, args.timeframe, f"{token}USDT") for token in tokens]

    processes = []

    def start_process(token, tf, pair):
        process = multiprocessing.Process(
            target=run_strategy, args=(token, tf, pair, args.version, args.sleep, args.mode, args.exchange)
        )
        process.start()
        return process

    active_processes = {}
    for token, time_frame, pair in strategies:
        process = start_process(token, time_frame, pair)
        active_processes[token] = (process, time_frame, pair)

    while True:
        time.sleep(30)
        for token, (process, tf, pair) in list(active_processes.items()):
            if not process.is_alive():
                logger.warning(f"Process for [{token}] on {tf} stopped. Restarting...")
                new_process = start_process(token, tf, pair)
                active_processes[token] = (new_process, tf, pair)
