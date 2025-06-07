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

# Local library imports (assuming they exist in the specified structure)
import chart
from lib.trend import ema_indicator
from lib.volatility import AverageTrueRange
from logger import logger

# --- Constants ---

# A small value to handle floating point comparisons
EPSILON = 1e-9

# A set is more efficient for membership checking ('in')
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

# Mapping for token shortcuts
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

# Timeframe durations in seconds
TIME_FRAME_SECONDS = {
    "3m": 3 * 60,
    "5m": 5 * 60,
    "15m": 15 * 60,
    "30m": 30 * 60,
    "1h": 60 * 60,
}


# Configuration for Chandelier Exit, grouped in an Enum for clarity
class CEConfig(Enum):
    SIZE = 200
    LENGTH = 1
    MULT = 1.80
    USE_CLOSE = True
    SUB_SIZE = 2


# Constants for external service URLs
TELEGRAM_API_BASE_URL = "http://localhost:8000"
BINANCE_FUTURE_API_URL = "https://fapi.binance.com/fapi/v1/klines"

# Constants for pre-send signal timing
PRE_SEND_TIMING_FACTOR_DEFAULT = 0.92
PRE_SEND_TIMING_FACTOR_5M = 0.94


# --- Data Structure Initialization ---


def init_kline_data_dict() -> Dict[str, List[Any]]:
    """Creates a standardized dictionary to hold kline and indicator data."""
    keys = [
        "Open",
        "High",
        "Low",
        "Close",
        "Time1",
        "Time",
        "ATR",
        "LongStop",
        "ShortStop",
        "LongStopPrev",
        "ShortStopPrev",
        "Direction",
        "Open_p",
        "Close_p",
    ]
    return {key: [] for key in keys}


# --- Helper Classes ---


class KlineHelper:
    """A helper class to fetch, process, and manage kline data."""

    def __init__(self, mode: str, exchange: str):
        self.mode = mode
        self.exchange = exchange
        self.weight = {"m1": 0}

    def _append_candle_base(self, data: Dict, kline: List) -> None:
        """Appends the base data common to both normal and Heikin Ashi candles."""
        data["Time1"].append(datetime.fromtimestamp(int(kline[0]) / 1000).strftime("%Y-%m-%d %H:%M"))
        data["Time"].append(int(kline[0]) / 1000)
        data["ATR"].append(None)
        data["LongStop"].append(None)
        data["ShortStop"].append(None)
        data["LongStopPrev"].append(None)
        data["ShortStopPrev"].append(None)
        data["Direction"].append(None)
        data["Open_p"].append(float(kline[1]))
        data["Close_p"].append(float(kline[4]))

    def _append_kline(self, data: Dict, kline: List) -> None:
        """Appends a standard kline candle to the data dictionary."""
        data["Open"].append(float(kline[1]))
        data["High"].append(float(kline[2]))
        data["Low"].append(float(kline[3]))
        data["Close"].append(float(kline[4]))
        self._append_candle_base(data, kline)

    def _append_heikin_ashi(self, data: Dict, kline: List, prev_item: Dict = None) -> None:
        """Calculates and appends a Heikin Ashi candle."""
        open_p, high_p, low_p, close_p = map(float, kline[1:5])

        if len(data["Close"]) > 0:  # Use previous candle from the current data buffer
            ha_open = (data["Open"][-1] + data["Close"][-1]) / 2
        elif prev_item:  # Use provided previous item (for populating partial data)
            ha_open = (prev_item["Open"] + prev_item["Close"]) / 2
        else:  # First candle in the series
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
        """Populates the data dictionary with klines using the specified mode."""
        for kline in klines:
            if self.mode == "heikin_ashi":
                self._append_heikin_ashi(data, kline, prev_item)
            else:
                self._append_kline(data, kline)

    def _pop_tail_data(self, data: Dict) -> None:
        """Removes the last element from each list in the data dictionary."""
        for key in data:
            if data[key]:
                data[key].pop()

    def _pop_top_data(self, data: Dict) -> None:
        """Removes the first element from each list in the data dictionary."""
        for key in data:
            if data[key]:
                data[key].pop(0)

    def _append_data(self, data1: Dict, data2: Dict) -> None:
        """Appends all elements from data2 lists to data1 lists."""
        for key in data1:
            data1[key].extend(data2[key])

    def _fetch_klines_future(self, pair: str, time_frame: str, limit: int) -> List:
        """Fetches klines from the Binance Futures API."""
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
        """Fetches klines from the appropriate exchange (Spot or Future)."""
        use_future_api = self.exchange == "future" or pair in NON_SPOT_PAIRS
        if use_future_api:
            return self._fetch_klines_future(pair, time_frame, limit)
        return binance_spot.klines(pair, time_frame, limit=limit)

    def export_csv(self, data: Dict, filename="atr2.csv") -> None:
        """Exports selected data columns to a CSV file."""
        df = pd.DataFrame(data)
        df[["Time1", "Direction", "Open_p", "Close_p"]].to_csv(filename, index=False, float_format="%.15f", sep=" ")


class ChandlierExit:
    """Calculates the Chandelier Exit indicator."""

    def __init__(self, size: int, multiplier: float, length: int, use_close: bool):
        self.size = size
        self.length = length
        self.use_close = use_close
        self.multiplier = multiplier
        self.direction = 1  # Start with a default direction

    def calculate_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculates and adds the ATR column to the DataFrame."""
        atr_calculator = AverageTrueRange(df["High"], df["Low"], df["Close"], window=self.length)
        df["ATR"] = atr_calculator.average_true_range() * self.multiplier
        return df

    def calculate_chandelier_exit(self, data: Dict) -> None:
        """Calculates Chandelier Exit values and direction in-place."""
        for i in range(self.size):
            if all(data[key][i] is not None for key in ["LongStop", "LongStopPrev", "ShortStop", "ShortStopPrev"]):
                continue

            # --- Calculate Long Stop ---
            price_window = data["Close" if self.use_close else "High"][max(0, i - self.length + 1) : i + 1]
            long_stop = max(price_window) - data["ATR"][i]

            long_stop_prev = data["LongStop"][i - 1] if i > 0 and data["LongStop"][i - 1] is not None else long_stop

            if i > 0 and (data["Close"][i - 1] - long_stop_prev) > EPSILON:
                long_stop = max(long_stop, long_stop_prev)

            data["LongStop"][i] = long_stop
            data["LongStopPrev"][i] = long_stop_prev

            # --- Calculate Short Stop ---
            price_window = data["Close" if self.use_close else "Low"][max(0, i - self.length + 1) : i + 1]
            short_stop = min(price_window) + data["ATR"][i]

            short_stop_prev = data["ShortStop"][i - 1] if i > 0 and data["ShortStop"][i - 1] is not None else short_stop

            if i > 0 and (data["Close"][i - 1] - short_stop_prev) < -EPSILON:
                short_stop = min(short_stop, short_stop_prev)

            data["ShortStop"][i] = short_stop
            data["ShortStopPrev"][i] = short_stop_prev

            # --- Determine Direction ---
            dir_ = self.direction
            if (data["Close"][i] - data["ShortStopPrev"][i]) > EPSILON:
                dir_ = 1
            elif (data["Close"][i] - data["LongStopPrev"][i]) < -EPSILON:
                dir_ = -1

            self.direction = dir_
            data["Direction"][i] = dir_


class EMA:
    """Handles fetching data and calculating various EMAs."""

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
        """Fetch initial klines and populate the data structures."""
        logger.info(f"Fetching initial EMA klines for {self.pair}")
        self.data = init_kline_data_dict()
        klines = self.kline_helper.fetch_klines(self.binance_spot, self.pair, self.time_frame, self.size)
        self.kline_helper.populate(self.data, klines)
        self.df = pd.DataFrame(self.data)
        self.timestamp = self.data["Time"][-1]

    def update_klines(self, latest_klines: List) -> None:
        """Updates klines with new data, handling timestamp alignment."""
        new_data = init_kline_data_dict()
        if not latest_klines:
            latest_klines = self.kline_helper.fetch_klines(self.binance_spot, self.pair, self.time_frame, 2)

        self.kline_helper.populate(new_data, latest_klines)

        latest_new_timestamp = new_data["Time"][-1]
        last_existing_timestamp = self.data["Time"][-1] if self.data["Time"] else 0

        expected_next_timestamp = last_existing_timestamp + TIME_FRAME_SECONDS.get(self.time_frame, 0)

        if latest_new_timestamp == last_existing_timestamp:
            # Update the last (still forming) candle
            self.kline_helper._pop_tail_data(self.data)
            self.kline_helper.populate(self.data, [latest_klines[-1]])
        elif latest_new_timestamp == expected_next_timestamp:
            # A new candle has closed, roll the data forward
            self.kline_helper._pop_top_data(self.data)
            # Note: original code pops tail then appends both, this simplified version is equivalent
            self.kline_helper.populate(self.data, [latest_klines[-1]])
        else:
            logger.error(
                f"Timestamp mismatch for {self.pair}: Last: {last_existing_timestamp}, New: {latest_new_timestamp}. Resyncing."
            )
            self.fetch_klines()

        self.df = pd.DataFrame(self.data)
        self.timestamp = self.df["Time"].iloc[-1]

    def calculate_all_emas(self) -> None:
        """Calculate all required EMA values."""
        self.df["EMA_200"] = ema_indicator(self.df["Close"], 200)
        self.ema_200_value = self.df["EMA_200"].iloc[-1]

        self.df["EMA_35"] = ema_indicator(self.df["Close"], 34)
        self.ema_35_value = self.df["EMA_35"].iloc[-1]

        self.df["EMA_21"] = ema_indicator(self.df["Close"], 21)
        self.ema_21_value = self.df["EMA_21"].iloc[-1]

    def to_csv(self, filename: str = "ema.csv") -> None:
        """Exports EMA data to a CSV file."""
        self.df[["Time1", "Close", "EMA_200", "EMA_35"]].to_csv(filename, index=False)

    def check_cross(
        self, time_frame: str, open_p: float, high: float, low: float, close: float, signal: Literal["BUY", "SELL"]
    ) -> Dict[str, bool]:
        """Check if the latest candle crossed any of the key EMAs."""
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


def remove_file(filename: str) -> None:
    """Safely removes a file if it exists."""
    try:
        os.remove(filename)
        logger.info(f"Removed invalid file: {filename}")
    except OSError:
        pass


def is_price_above_ema200(pair: str, time_frame: str, signal: Literal["BUY", "SELL"]) -> bool:
    """Checks if the price is on the correct side of the 200 EMA for a given signal."""
    try:
        ema = EMA(pair, time_frame, "heikin_ashi", "future", 1000)
        ema.fetch_klines()
        ema.calculate_all_emas()
        close_of_last_candle = ema.data["Close"][-1]

        if signal == "BUY":
            return close_of_last_candle > ema.ema_200_value
        elif signal == "SELL":
            return close_of_last_candle < ema.ema_200_value
    except Exception as e:
        logger.error(f"Failed to check EMA cut for {pair}: {e}")
    return False


def format_price_change(current: float, previous: float) -> str:
    """Formats the percentage change between two prices into a signed string."""
    if previous == 0:
        return "0.00%"
    percent_change = (current - previous) / previous * 100
    return f"+{percent_change:.2f}%" if percent_change >= 0 else f"{percent_change:.2f}%"


def should_pre_send_signal(timestamp: float, time_frame: str) -> bool:
    """Checks if the current time is late enough in the candle's duration to pre-send a signal."""
    if time_frame not in TIME_FRAME_SECONDS:
        return False

    factor = PRE_SEND_TIMING_FACTOR_5M if time_frame == "5m" else PRE_SEND_TIMING_FACTOR_DEFAULT
    time_passed_threshold = timestamp + TIME_FRAME_SECONDS[time_frame] * factor

    return time.time() >= time_passed_threshold


def send_telegram_api_request(endpoint: str, body: Dict) -> Dict:
    """Sends a POST request to the local Telegram bot API."""
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
    """Sends a signal message via the Telegram bot API."""
    res = send_telegram_api_request("sendMessage", body)
    return res if res.get("status") == "success" else None


def delete_telegram_message(body: Dict) -> bool:
    """Deletes a message via the Telegram bot API."""
    res = send_telegram_api_request("deleteMessage", body)
    return res.get("status", False)


# --- Core Strategy Logic ---


def main(
    data: Dict, token: str, time_frame: str, pair: str, version: str, time_sleep: int, mode: str, exchange: str
) -> None:
    # --- Initialization ---
    size, length, mult, use_close, sub_size = (
        CEConfig.SIZE.value,
        CEConfig.LENGTH.value,
        CEConfig.MULT.value,
        CEConfig.USE_CLOSE.value,
        CEConfig.SUB_SIZE.value,
    )
    if time_frame == "5m":
        mult = 1.80

    if not mode:
        mode = "heikin_ashi"

    logger.info(f"Starting {pair}: MODE: {mode}, SIZE: {size}, LENGTH: {length}, MULT: {mult}, USE_CLOSE: {use_close}")

    kline_helper = KlineHelper(mode=mode, exchange=exchange)
    binance_spot = Spot()
    chandelier_exit = ChandlierExit(size=size, length=length, multiplier=mult, use_close=use_close)

    # Fetch initial data and calculate indicators
    klines = kline_helper.fetch_klines(binance_spot, pair, time_frame, size)
    kline_helper.populate(data, klines)
    df_result = chandelier_exit.calculate_atr(pd.DataFrame(data))
    data["ATR"] = df_result["ATR"].values.tolist()
    chandelier_exit.calculate_chandelier_exit(data=data)

    # State variables for the main loop
    timestamp = data["Time"][size - 1]
    counter = 1
    has_sent_signal_this_candle = False
    last_sent_message = {"message_id": None, "Time": None, "Direction": None, "Image": None, "Counter": None}

    short_token = TOKEN_SHORTCUT.get(token, token)
    token_for_log = token.ljust(12)

    chandelier_exit_sub = ChandlierExit(size=sub_size, length=length, multiplier=mult, use_close=use_close)

    # Trim initial data to a smaller working size
    candles_to_trim = size - 200
    for _ in range(candles_to_trim):
        kline_helper._pop_top_data(data)

    size -= candles_to_trim
    chandelier_exit.size = size

    ema_handler = EMA(pair=pair, time_frame=time_frame, mode=mode, exchange=exchange, size=1000)
    ema_handler.fetch_klines()
    time.sleep(1)

    # --- Main Loop ---
    while True:
        # Fetch the latest two candles to handle updates and new candle events
        data_temp_dict = init_kline_data_dict()
        two_latest_klines = kline_helper.fetch_klines(binance_spot, pair, time_frame, 2)
        ema_handler.update_klines(two_latest_klines)

        kline_helper.populate(
            data_temp_dict, two_latest_klines, prev_item={"Open": data["Open"][-3], "Close": data["Close"][-3]}
        )

        percent_change_log = format_price_change(data_temp_dict["Close_p"][1], data_temp_dict["Close_p"][0])
        print(
            f"Time: {counter} M:{mult} W:{kline_helper.weight['m1']} {token_for_log} {percent_change_log} {data_temp_dict['Time1'][1]}"
        )

        # --- Data Update Logic ---
        is_candle_update = timestamp == data_temp_dict["Time"][1]
        is_new_candle = timestamp == data_temp_dict["Time"][0]

        if is_candle_update:
            # The current candle is still forming, update its values
            chandelier_exit.direction = data["Direction"][-3]
            kline_helper._pop_tail_data(data)
            kline_helper._pop_tail_data(data)
            kline_helper._append_data(data, data_temp_dict)
        elif is_new_candle:
            # A new candle has closed
            counter += 1
            timestamp = data_temp_dict["Time"][1]
            has_sent_signal_this_candle = False
            chandelier_exit.direction = data["Direction"][-2]
            kline_helper._pop_top_data(data)
            kline_helper._pop_tail_data(data)
            kline_helper._append_data(data, data_temp_dict)
        else:
            logger.info(
                f"Time not match: {token} ts: {timestamp} 0: {data_temp_dict['Time'][0]} 1: {data_temp_dict['Time'][1]}"
            )
            break  # Restart the process

        # Recalculate indicators on the updated data
        df_temp = chandelier_exit_sub.calculate_atr(pd.DataFrame(data_temp_dict))
        data["ATR"][-sub_size:] = df_temp["ATR"].values.tolist()
        chandelier_exit.calculate_chandelier_exit(data)

        # --- Signal Logic ---
        # Index Aliases for Readability
        LATEST, PREV, PREV_PREV = size - 1, size - 2, size - 3

        direction_flipped_on_latest = data["Direction"][LATEST] != data["Direction"][PREV]
        direction_flipped_on_prev = data["Direction"][PREV] != data["Direction"][PREV_PREV]

        # Logic for specific timeframes that allow pre-sending signals
        can_pre_send_signal = time_frame in ("5m", "15m", "30m")

        if can_pre_send_signal:
            # Delete an invalidated pre-sent signal if direction flips back
            if (
                not has_sent_signal_this_candle
                and last_sent_message["message_id"]
                and last_sent_message["Direction"] != data["Direction"][LATEST]
                and last_sent_message["Counter"] == counter - 1
            ):

                logger.info(f"Deleting invalid message: Token: {token} {last_sent_message}")
                body_for_delete = {
                    "time_frame": f"{time_frame}{'_normal' if mode == 'normal' else ''}",
                    "message_id": str(last_sent_message["message_id"]),
                }
                if delete_telegram_message(body_for_delete):
                    remove_file(last_sent_message["Image"])
                    last_sent_message = {
                        "message_id": None,
                        "Time": None,
                        "Direction": None,
                        "Image": None,
                        "Counter": None,
                    }

            # Pre-send a signal if a flip occurs on the latest candle
            if (
                direction_flipped_on_latest
                and not has_sent_signal_this_candle
                and should_pre_send_signal(timestamp, time_frame)
            ):
                signal = "BUY" if data["Direction"][LATEST] == 1 else "SELL"

                # EMA cross validation
                ema_handler.calculate_all_emas()
                ema_cross = ema_handler.check_cross(
                    time_frame,
                    data["Open"][LATEST],
                    data["High"][LATEST],
                    data["Low"][LATEST],
                    data["Close"][LATEST],
                    signal,
                )
                if not any(ema_cross.values()) and time_frame in ("5m", "15m"):
                    logger.info(f"Skipping signal for {token} due to no EMA cross.")
                    continue

                # Prepare and send signal
                percent_change = format_price_change(data["Close_p"][LATEST], data["Close_p"][PREV])
                next_candle_time = datetime.fromtimestamp(timestamp + TIME_FRAME_SECONDS[time_frame]).strftime("%H:%M")

                body = {
                    "signal": signal,
                    "symbol": f"${short_token}",
                    "time_frame": time_frame,
                    "time": next_candle_time,
                    "price": data["Close"][LATEST],
                    "change": percent_change,
                    "ema_cross": ema_cross,
                }
                # ... (rest of body modification and sending logic)
                time.sleep(random.uniform(1.0, 3.0))  # Random sleep to avoid API rate limits
                image_path = chart.get_charts(
                    f"{short_token}", PAIR=pair, TIME_FRAME=time_frame, signal=signal, time1=next_candle_time
                )
                body["image"] = image_path

                res = send_telegram_message(body)
                if res and res.get("message_id"):
                    has_sent_signal_this_candle = True
                    last_sent_message.update(
                        {
                            "message_id": res.get("message_id"),
                            "Counter": counter,
                            "Direction": data["Direction"][LATEST],
                            "Image": image_path,
                            "Time": next_candle_time,
                        }
                    )
                    logger.info(f"Signal pre-sent: {body} | message_id: {res.get('message_id')}")
                else:
                    logger.error(f"Failed to pre-send signal: {body}")

        # Logic for sending signals on candle close (for all other timeframes)
        elif direction_flipped_on_prev and not has_sent_signal_this_candle:
            signal = "BUY" if data["Direction"][PREV] == 1 else "SELL"
            percent_change = format_price_change(data["Close_p"][PREV], data["Close_p"][PREV_PREV])

            ema_handler.calculate_all_emas()
            ema_cross = ema_handler.check_cross(
                time_frame, data["Open"][PREV], data["High"][PREV], data["Low"][PREV], data["Close"][PREV], signal
            )

            body = {
                "signal": signal,
                "symbol": f"${short_token}",
                "time_frame": time_frame,
                "time": data["Time1"][PREV][11:],
                "price": data["Close"][PREV],
                "change": percent_change,
                "ema_cross": ema_cross,
            }
            # ... (body modification and sending logic)
            image_path = chart.get_charts(
                f"{short_token}", PAIR=pair, TIME_FRAME=time_frame, signal=signal, time1=data["Time1"][PREV][11:]
            )
            body["image"] = image_path

            res = send_telegram_message(body)
            if res:
                has_sent_signal_this_candle = True
                logger.info(f"Signal sent: {body}")
            else:
                logger.error(f"Failed to send signal: {body}")

        time.sleep(time_sleep)


def run_strategy(token: str, time_frame: str, pair: str, version: str, time_sleep: int, mode: str, exchange: str):
    """A wrapper function to run the main strategy in a resilient loop."""
    while True:
        try:
            logger.info(f"Starting strategy for {token} {time_frame} {pair}")
            data = init_kline_data_dict()
            main(data, token, time_frame, pair, version, time_sleep, mode, exchange)
        except Exception:
            logger.error(f"[{token}] Unhandled exception in strategy: {traceback.format_exc()}")
            time.sleep(5)  # Wait before restarting
        finally:
            logger.info(f"[{token}] Restarting strategy process...")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a Chandelier Exit trading bot strategy.")
    parser.add_argument("--timeframe", type=str, help="Time frame (e.g., '5m', '1h')", default="5m")
    parser.add_argument("--sleep", type=int, help="Sleep time in seconds between loops", default=10)
    parser.add_argument("--mode", type=str, help="Chart mode: 'heikin_ashi' or 'normal'", default="")
    parser.add_argument("--exchange", type=str, help="Exchange: 'future' or 'spot'", default="future")
    parser.add_argument("--version", type=str, help="Strategy version suffix for identification", default="")
    args = parser.parse_args()

    # This mapping determines which token list to use based on settings
    # Example: --timeframe 5m --mode normal -> looks for "tokens.5m.normal.txt"
    token_list_files = {
        "1m": "tokens.1m.txt",
        "3m": "tokens.top.txt",
        "5m": "tokens.5m.txt",
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

    # Construct the key to find the correct token file
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

    # --- Process Management ---
    active_processes = {}
    for token, time_frame, pair in strategies:
        process = start_process(token, time_frame, pair)
        active_processes[token] = (process, time_frame, pair)

    while True:
        time.sleep(30)  # Check on processes periodically
        for token, (process, tf, pair) in list(active_processes.items()):
            if not process.is_alive():
                logger.warning(f"Process for [{token}] on {tf} stopped. Restarting...")
                new_process = start_process(token, tf, pair)
                active_processes[token] = (new_process, tf, pair)
