# Description: This script is used to backtest the Chandelier Exit strategy on Binance Futures.

import time
import pandas as pd
from ta.volatility import AverageTrueRange
from binance.spot import Spot
from enum import Enum
from datetime import datetime, timedelta
import requests
import json
import argparse

EPSILON = 1e-9

NON_SPOT_PAIRS = {
    "TONUSDT": "TONUSDT",
    "ONDOUSDT": "ONDOUSDT",
    "1000PEPEUSDT": "1000PEPEUSDT",
    "1000BONKUSDT": "1000BONKUSDT",
}

# Define the maximum number of klines per request
MAX_KLINES = 1000

START_DATE = "2024-06-20"
END_DATE = "2024-08-02"
MODE = "KLINE"
EXCHANGE = "future"


class CEConfig(Enum):
    SIZE = 200
    LENGTH = 1
    MULT = 1.8
    USE_CLOSE = True
    SUB_SIZE = 2


class TIME_FRAME_STR(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"


TIME_FRAME_MS = {
    "1m": 60,
    "5m": 5 * 60,
    "15m": 15 * 60,
    "1h": 60 * 60,
}


class KlineHelper:
    def _append_kline(self, data, kline):
        open_p = float(kline[1])
        high_p = float(kline[2])
        low_p = float(kline[3])
        close_p = float(kline[4])
        time1 = datetime.fromtimestamp(int(kline[0]) / 1000).strftime("%Y-%m-%d %H:%M")
        time = int(kline[0]) / 1000

        data["Open"].append(open_p)
        data["High"].append(high_p)
        data["Low"].append(low_p)
        data["Close"].append(close_p)
        data["Time1"].append(time1)
        data["Time"].append(time)
        data["ATR"].append(None)
        data["LongStop"].append(None)
        data["ShortStop"].append(None)
        data["LongStopPrev"].append(None)
        data["ShortStopPrev"].append(None)
        data["direction"].append(None)
        data["real_price_open"].append(open_p)
        data["real_price_close"].append(close_p)

        if len(data["real_price_close"]) > 1:  # Ensure there's a previous close price to compare
            prev_close_price = data["real_price_close"][-2]
            change = (close_p - prev_close_price) / prev_close_price * 100
        else:
            change = None
        data["real_price_change"].append(change)

    def _append_heikin_ashi(self, data, kline, prev_item=None):
        open_p = float(kline[1])
        high_p = float(kline[2])
        low_p = float(kline[3])
        close_p = float(kline[4])
        time1 = datetime.fromtimestamp(int(kline[0]) / 1000).strftime("%Y-%m-%d %H:%M")
        time = int(kline[0]) / 1000

        if len(data["Close"]) > 0:  # Check isnt the first candle
            heikin_ashi_open = (data["Open"][-1] + data["Close"][-1]) / 2
            heikin_ashi_close = (open_p + high_p + low_p + close_p) / 4
            heikin_ashi_high = max(high_p, heikin_ashi_open, heikin_ashi_close)
            heikin_ashi_low = min(low_p, heikin_ashi_open, heikin_ashi_close)
        else:
            if prev_item:
                heikin_ashi_open = (prev_item["Open"] + prev_item["Close"]) / 2
                heikin_ashi_close = (open_p + high_p + low_p + close_p) / 4
                heikin_ashi_high = max(high_p, heikin_ashi_open, heikin_ashi_close)
                heikin_ashi_low = min(low_p, heikin_ashi_open, heikin_ashi_close)
            else:
                heikin_ashi_open = open_p
                heikin_ashi_close = close_p
                heikin_ashi_high = high_p
                heikin_ashi_low = low_p

        data["Open"].append(heikin_ashi_open)
        data["High"].append(heikin_ashi_high)
        data["Low"].append(heikin_ashi_low)
        data["Close"].append(heikin_ashi_close)
        data["Time1"].append(time1)
        data["Time"].append(time)
        data["ATR"].append(None)
        data["LongStop"].append(None)
        data["ShortStop"].append(None)
        data["LongStopPrev"].append(None)
        data["ShortStopPrev"].append(None)
        data["direction"].append(None)
        """
        real_price_* : Real price of the candle, not Heikin Ashi
        """

        data["real_price_open"].append(open_p)
        data["real_price_close"].append(close_p)

        if len(data["real_price_close"]) > 1:  # Ensure there's a previous close price to compare
            prev_close_price = data["real_price_close"][-2]
            change = (close_p - prev_close_price) / prev_close_price * 100
        else:
            change = None
        data["real_price_change"].append(change)

    def get_kline_data(self, data, klines, prev_item=None):
        for kline in klines:
            if MODE == "KLINE":
                self._append_kline(data, kline)
            else:
                self._append_heikin_ashi(data, kline)

    def export_csv(self, data, filename="atr2.csv"):
        dfdata = pd.DataFrame(data)
        dfdata[
            [
                "Time",
                "Time1",
                "direction",
                "High",
                "Low",
                "real_price_open",
                "real_price_close",
                "real_price_change",
                "LongStop",
                "ShortStop",
            ]
        ].to_csv(filename)


class ChandlierExit:
    def __init__(self, size, multiplier=2.0, length=1, use_close=True):
        self.size = size
        self.length = length
        self.use_close = use_close
        self.multiplier = multiplier
        self.direction = 1

    def calculate_atr(self, df):
        atr_calculator = AverageTrueRange(df["High"], df["Low"], df["Close"], window=self.length)
        df["ATR"] = atr_calculator.average_true_range() * self.multiplier
        return df

    def calculate_chandelier_exit(self, data):
        for i in range(self.size):
            if data["LongStop"][i] and data["LongStopPrev"][i] and data["ShortStop"][i] and data["ShortStopPrev"][i]:
                continue
            else:
                pass

            # Calculate Long Stop
            longStop = (
                max(data["Close"][max(0, i - self.length + 1) : i + 1]) if self.use_close else max(data["High"][max(0, i - self.length + 1) : i + 1])
            ) - data["ATR"][i]

            longStopPrev = data["LongStop"][i - 1] if data["LongStop"][i - 1] is not None else longStop

            if data["Close"][i - 1] - longStopPrev > EPSILON:
                longStop = max(longStop, longStopPrev)
            else:
                longStop = longStop

            data["LongStop"][i] = longStop
            data["LongStopPrev"][i] = longStopPrev

            # Calculate Short Stop
            shortStop = (
                min(data["Close"][max(0, i - self.length + 1) : i + 1]) if self.use_close else min(data["Low"][max(0, i - self.length + 1) : i + 1])
            ) + data["ATR"][i]

            shortStopPrev = data["ShortStop"][i - 1] if data["ShortStop"][i - 1] is not None else shortStop

            if data["Close"][i - 1] - shortStopPrev < -EPSILON:
                shortStop = min(shortStop, shortStopPrev)
            else:
                shortStop = shortStop

            data["ShortStop"][i] = shortStop
            data["ShortStopPrev"][i] = shortStopPrev

            dir = self.direction

            if data["Close"][i] - data["ShortStopPrev"][i] > EPSILON:
                dir = 1
            elif data["Close"][i] - data["LongStopPrev"][i] < -EPSILON:
                dir = -1

            self.direction = dir
            data["direction"][i] = dir


def fetch_klines_non_spot(PAIR, TIME_FRAME, startTimeMs, endTimeMs, limit):
    URL = f"https://fapi.binance.com/fapi/v1/klines?symbol={PAIR}&interval={TIME_FRAME}&startTime={startTimeMs}&endTime={endTimeMs}&limit={limit}"
    headers = {"Content-Type": "application/json"}
    res = requests.get(URL, headers=headers, timeout=None)
    return res.json()


def fetch_klines(binance_spot: Spot, PAIR, TIME_FRAME, startTimeMs, endTimeMs, limit):
    if EXCHANGE == "future":
        return fetch_klines_non_spot(PAIR, TIME_FRAME, limit=limit, startTimeMs=startTimeMs, endTimeMs=endTimeMs)
    if PAIR in NON_SPOT_PAIRS:
        return fetch_klines_non_spot(PAIR, TIME_FRAME, startTimeMs, endTimeMs, limit)
    return binance_spot.klines(PAIR, TIME_FRAME, limit=limit, startTime=startTimeMs, endTime=endTimeMs)


def fetch_klines_by_date_range(binance_spot: Spot, PAIR, TIME_FRAME, start_date_str=None, end_date_str=None):
    if end_date_str:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    else:
        end_date = datetime.utcnow()

    if start_date_str:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    else:
        start_date = end_date - timedelta(days=1)  # Adjust as necessary to fetch klines up to the latest available

    startTimeMs = int(start_date.timestamp() * 1000)
    endTimeMs = int((end_date + timedelta(days=1)).timestamp() * 1000)  # Include the end day fully

    klines = []
    current_start_time = startTimeMs

    while current_start_time < endTimeMs:
        # Calculate the next end time for the request
        next_end_time = min(
            current_start_time + MAX_KLINES * get_milliseconds(TIME_FRAME),
            endTimeMs,
        )

        # Fetch klines
        data = fetch_klines(
            binance_spot,
            PAIR,
            TIME_FRAME,
            current_start_time,
            next_end_time,
            MAX_KLINES,
        )

        # Append to the klines list
        klines.extend(data)

        # Move the start time forward
        current_start_time = int(data[-1][0]) + get_milliseconds(TIME_FRAME)  # Move to the next kline start time

    return klines


def get_milliseconds(time_frame):
    # Helper function to convert time frame to milliseconds
    unit = time_frame[-1]
    value = int(time_frame[:-1])
    if unit == "m":
        return value * 60 * 1000
    elif unit == "h":
        return value * 60 * 60 * 1000
    elif unit == "d":
        return value * 24 * 60 * 60 * 1000
    elif unit == "w":
        return value * 7 * 24 * 60 * 60 * 1000
    else:
        raise ValueError("Unsupported time frame unit")


def main(data, TOKEN, TIME_FRAME, PAIR, MONTH, YEAR):
    (SIZE, LENGTH, MULT, USE_CLOSE, SUB_SIZE) = (
        CEConfig.SIZE.value,
        CEConfig.LENGTH.value,
        CEConfig.MULT.value,
        CEConfig.USE_CLOSE.value,
        CEConfig.SUB_SIZE.value,
    )
    print(f"Starting {PAIR}: SIZE: {SIZE}, LENGTH: {LENGTH}, MULT: {MULT}, USE_CLOSE: {USE_CLOSE}")

    kline_helper = KlineHelper()
    binance_spot = Spot()

    # Get klines for the month
    klines = fetch_klines_by_date_range(
        binance_spot,
        PAIR,
        TIME_FRAME,
        start_date_str=START_DATE,
        end_date_str=END_DATE,
    )
    kline_helper.get_kline_data(data, klines)
    df_data = pd.DataFrame(data)

    SIZE = len(df_data)
    chandelier_exit = ChandlierExit(size=SIZE, length=LENGTH, multiplier=MULT, use_close=USE_CLOSE)
    # Calculate ATR
    df_result = chandelier_exit.calculate_atr(df=df_data)

    # Update ATR to data
    data["ATR"] = df_result["ATR"].values.tolist()

    # Calculate Chandelier Exit
    chandelier_exit.calculate_chandelier_exit(data=data)

    if MODE == "KLINE":
        kline_helper.export_csv(data, filename=f"{TOKEN}_ce_{time_frame}.csv")
    else:
        kline_helper.export_csv(data, filename=f"{TOKEN}_ce_{time_frame}_ha.csv")


def init_data():
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
        "direction",
        "real_price_open",
        "real_price_close",
        "real_price_change",
    ]

    data = {key: [] for key in keys}
    return data


import multiprocessing


def run_strategy(token, time_frame, pair, MONTH, YEAR):
    try:
        print("STARTING CE BOT")
        data = init_data()
        main(data, token, time_frame, pair, MONTH, YEAR)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process trading pair and timeframe.")
    parser.add_argument("--timeframe", type=str, help='Time frame, e.g., "1m"', default="1m")
    parser.add_argument("--month", type=str, help="Month to backtest", default=1)
    parser.add_argument("--year", type=str, help="Year to backtest", default=2024)

    args = parser.parse_args()
    TIME_FRAME = args.timeframe
    MONTH = int(args.month)
    YEAR = int(args.year)

    # Each .txt file for each time frame
    files = {
        "1m": "tokens.1m.txt",
        "3m": "tokens.txt",
        "5m": "tokens.15m.txt",
        "15m": "tokens.15m.txt",
        "30m": "tokens.15m.txt",
        "1h": "tokens.15m.txt",
        "2h": "tokens.15m.txt",
        "4h": "tokens.15m.txt",
    }

    with open(files[TIME_FRAME], "r") as file:
        tokens = [line.strip() for line in file]

    strategies = [(token, TIME_FRAME, f"{token}USDT") for token in tokens]

    processes = []
    for token, time_frame, pair in strategies:
        process = multiprocessing.Process(target=run_strategy, args=(token, time_frame, pair, MONTH, YEAR))
        processes.append(process)
        process.start()
