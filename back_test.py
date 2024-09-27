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
from zlma import calculate_zlsma, fetch_zlsma

EPSILON = 1e-9

NON_SPOT_PAIRS = {
    "TONUSDT": "TONUSDT",
    "ONDOUSDT": "ONDOUSDT",
    "1000PEPEUSDT": "1000PEPEUSDT",
    "1000BONKUSDT": "1000BONKUSDT",
}

# Define the maximum number of klines per request
MAX_KLINES = 1000

START_DATE = "2024-06-01"
END_DATE = "2024-06-30"
MODE = "HA"  # KLINE or HEIKIN ASHI
EXCHANGE = "future"

ZLSMA_LENGTH_50 = 50
ZLSMA_OFFSET = 0

ZLSMA_LENGTH_32 = 32


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
        data["signal"].append(0)

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
        data["signal"].append(0)

    def get_kline_data(self, data, klines, prev_item=None):
        for kline in klines:
            if MODE == "KLINE":
                self._append_kline(data, kline)
            else:
                self._append_heikin_ashi(data, kline)

    def export_csv(self, data, filename="atr2.csv"):
        dfdata = pd.DataFrame(data)
        dfdata.to_csv(filename)


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
    print(f"Fetching klines for {PAIR} from {datetime.fromtimestamp(startTimeMs / 1000)} to {datetime.fromtimestamp(endTimeMs / 1000)}")
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

    print("Calculating ZLSMA")
    calculate_zlsma(data, key="ZLSMA_32", length=ZLSMA_LENGTH_32, offset=ZLSMA_OFFSET)
    calculate_zlsma(data, key="ZLSMA_50", length=ZLSMA_LENGTH_50, offset=ZLSMA_OFFSET)

    print("Exporting CSV")

    if MODE == "KLINE":
        kline_helper.export_csv(data, filename=f"{TOKEN}_ce_{time_frame}_{CEConfig.MULT.value}.csv")
    else:
        kline_helper.export_csv(data, filename=f"{TOKEN}_ce_{time_frame}_{CEConfig.MULT.value}_HA.csv")


def init_data():
    keys = [
        "Time1",
        "direction",
        "signal",
        "Open",
        "High",
        "Low",
        "Close",
        "Time",
        "ATR",
        "LongStop",
        "ShortStop",
        "LongStopPrev",
        "ShortStopPrev",
        "real_price_open",
        "real_price_close",
        "real_price_change",
    ]

    data = {key: [] for key in keys}
    return data


import multiprocessing
import traceback


def run_strategy(token, time_frame, pair, MONTH, YEAR):
    try:
        print("STARTING CE BOT")
        data = init_data()
        main(data, token, time_frame, pair, MONTH, YEAR)
    except Exception as e:
        print(traceback.format_exc())
        print(f"Error: {e}")
        time.sleep(5)


def extract_signals(mode, TIME_FRAME):
    files = {
        "1m": "tokens.15m.txt",
        "3m": "tokens.15m.txt",
        "5m": "tokens.15m.txt",
        "15m": "tokens.15m.txt",
        "30m": "tokens.15m.txt",
        "1h": "tokens.15m.txt",
        "2h": "tokens.15m.txt",
        "4h": "tokens.15m.txt",
    }

    try:
        with open(files[TIME_FRAME], "r") as file:
            tokens = [line.strip() for line in file]
    except FileNotFoundError:
        print(f"File not found for time frame {TIME_FRAME}")
        return

    # Build the list of files to extract data from
    files_to_extract = [f"{token}_ce_{TIME_FRAME}_{CEConfig.MULT.value}_{mode}.csv" for token in tokens]

    # Read CSVs and store DataFrames along with their tokens
    dfs = [{"df": pd.read_csv(file), "token": file.split("_")[0], "file": file} for file in files_to_extract]

    # Check if data is available
    if not dfs or len(dfs[0]["df"]) == 0:
        print("No data found in the CSVs.")
        return

    size = len(dfs[0]["df"])  # Get number of rows from the first DataFrame


    # token counter, dict with key as token and value as 0

    counter = {token: 0 for token in tokens}

    # Process signals from index 128 onwards
    for i in range(128, size):
        long_signal = []
        short_signal = []
        final = []
        is_long = False  # Flag to track if it's a long signal

        # Loop through DataFrames and determine signal direction
        for df_dict in dfs:
            df_data = df_dict["df"]

            # Ensure 'direction' column exists
            if "direction" not in df_data.columns:
                continue

            cur = df_data["direction"].iloc[i]
            pre = df_data["direction"].iloc[i - 1]
            pre_pre = df_data["direction"].iloc[i - 2]

            # Check for long signal
            if cur == 1 and pre == -1 and pre_pre == -1:
                long_signal.append(df_dict["token"])

            # Check for short signal
            elif cur == -1 and pre == 1 and pre_pre == 1:
                short_signal.append(df_dict["token"])

        # Determine which signal is stronger and ensure final has at least 3 tokens
        if len(long_signal) >= len(short_signal) and len(long_signal) >= 3:
            final = long_signal
            is_long = True
        elif len(short_signal) >= len(long_signal) and len(short_signal) >= 3:
            final = short_signal

        # Only add a signal if final has 3 or more tokens
        if len(final) >= 3:
            type = "LONG" if is_long else "SHORT"
            print(f"Signal {type} detected at index {i}, time: {df_data['Time1'].iloc[i]} with tokens: {final}")
            # Add a new column "signal" to the DataFrames for the tokens in final
            for df_dict in dfs:
                if df_dict["token"] in final:
                    # Set signal value: 1 for long, -1 for short
                    counter[df_dict["token"]] += 1
                    df_dict["df"].at[i, "signal"] = 1 if is_long else -1

    # Save each DataFrame back to its respective CSV file
    for df_dict in dfs:
        df_dict["df"].to_csv(df_dict["file"], index=False)  # Save without the index column
        print(f"Updated {df_dict['file']} with new signals.")


    print(f"Token Counter: {counter}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process trading pair and timeframe.")
    parser.add_argument("--timeframe", type=str, help='Time frame, e.g., "1m"', default="1m")
    parser.add_argument("--month", type=str, help="Month to backtest", default=1)
    parser.add_argument("--year", type=str, help="Year to backtest", default=2024)
    parser.add_argument("--mode", type=str, help="Year to backtest", default="KLINE")

    args = parser.parse_args()
    TIME_FRAME = args.timeframe
    MONTH = int(args.month)
    YEAR = int(args.year)
    MODE = args.mode

    # Each .txt file for each time frame
    files = {
        "1m": "tokens.15m.txt",
        "3m": "tokens.15m.txt",
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

    for process in processes:
        process.join()

    print("All processes completed.")
    print("Extracting signals...")
    extract_signals(MODE, TIME_FRAME)

# Token Counter: {'1000PEPE': 245, '1000FLOKI': 230, 'BOME': 229, '1000BONK': 179, 'ORDI': 202, 'WIF': 190, 'NOT': 204, 'TON': 142, 'PEOPLE': 170, '1000SATS': 134, 'ZRO': 147, 'IO': 153, 'TIA': 189, 'WLD': 178, 'SUI': 224}
# Token Counter: {'1000PEPE': 170, '1000FLOKI': 157, 'BOME': 144, '1000BONK': 125, 'ORDI': 132, 'WIF': 117, 'NOT': 135, 'TON': 90, 'PEOPLE': 109, '1000SATS': 83, 'ZRO': 87, 'IO': 97, 'TIA': 117, 'WLD': 109, 'SUI': 145}