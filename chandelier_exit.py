import time
import pandas as pd
from ta.volatility import AverageTrueRange
from binance.spot import Spot
from enum import Enum
from datetime import datetime
import requests
import json
import argparse

Epsilon = 1e-9


class CEConfig(Enum):
    SIZE = 200
    LENGTH = 1
    MULT = 2
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
    def _append_heikin_ashi(self, data, kline, prev_item=None):
        open_p = float(kline[1])
        high_p = float(kline[2])
        low_p = float(kline[3])
        close_p = float(kline[4])
        time1 = datetime.fromtimestamp(int(kline[0]) / 1000).strftime("%Y-%m-%d %H:%M:%S")
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
        data["Direction"].append(None)
        data["Open_p"].append(open_p)
        data["Close_p"].append(close_p)

    def get_heikin_ashi(self, data, klines, prev_item=None):
        for kline in klines:
            self._append_heikin_ashi(data, kline, prev_item)

    def _pop_tail_data(self, data):
        for key in data:
            data[key].pop()

    def _pop_top_data(self, data):
        for key in data:
            data[key].pop(0)

    def _append_data(self, data1, data2):
        for key in data1:
            data1[key].extend(data2[key])

    def export_csv(self, data, filename="atr2.csv"):
        dfdata = pd.DataFrame(data)
        dfdata[["Time1", "Open_p", "Close_p"]].to_csv(
            filename, index=False, float_format="%.15f", sep=" "
        )


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
                max(data["Close"][max(0, i - self.length + 1) : i + 1])
                if self.use_close
                else max(data["High"][max(0, i - self.length + 1) : i + 1])
            ) - data["ATR"][i]

            longStopPrev = data["LongStop"][i - 1] if data["LongStop"][i - 1] is not None else longStop

            if data["Close"][i - 1] - longStopPrev > Epsilon:
                longStop = max(longStop, longStopPrev)
            else:
                longStop = longStop

            data["LongStop"][i] = longStop
            data["LongStopPrev"][i] = longStopPrev

            # Calculate Short Stop
            shortStop = (
                min(data["Close"][max(0, i - self.length + 1) : i + 1])
                if self.use_close
                else min(data["Low"][max(0, i - self.length + 1) : i + 1])
            ) + data["ATR"][i]

            shortStopPrev = data["ShortStop"][i - 1] if data["ShortStop"][i - 1] is not None else shortStop

            if data["Close"][i - 1] - shortStopPrev < -Epsilon:
                shortStop = min(shortStop, shortStopPrev)
            else:
                shortStop = shortStop

            data["ShortStop"][i] = shortStop
            data["ShortStopPrev"][i] = shortStopPrev

            dir = self.direction

            if data["Close"][i] - data["ShortStopPrev"][i] > Epsilon:
                dir = 1
            elif data["Close"][i] - data["LongStopPrev"][i] < -Epsilon:
                dir = -1

            self.direction = dir
            data["Direction"][i] = dir


def send_telegram_message(body):
    URL = "http://localhost:8000/sendMessage"
    headers = {"Content-Type": "application/json"}
    requests.post(URL, headers=headers, data=json.dumps(body))


def main(data, TOKEN, TIME_FRAME, PAIR, TIME_SLEEP):
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
    chandelier_exit = ChandlierExit(size=SIZE, length=LENGTH, multiplier=MULT, use_close=USE_CLOSE)

    # Get 500 Klines
    klines = binance_spot.klines(PAIR, TIME_FRAME, limit=SIZE)
    kline_helper.get_heikin_ashi(data, klines)
    df_data = pd.DataFrame(data)

    # Calculate ATR
    df_result = chandelier_exit.calculate_atr(df=df_data)

    # Update ATR to data
    data["ATR"] = df_result["ATR"].values.tolist()

    # Calculate Chandelier Exit
    chandelier_exit.calculate_chandelier_exit(data=data)

    # Save the last time
    timestamp = data["Time"][SIZE - 1]

    counter = 0
    hasSentSignal = False
    _token = TOKEN.ljust(8)
    chandelier_exit_2 = ChandlierExit(size=SUB_SIZE, length=LENGTH, multiplier=MULT, use_close=USE_CLOSE)

    # Remove 150 data
    for i in range(170):
        kline_helper._pop_top_data(data)
    chandelier_exit.size = SIZE - 170
    SIZE = SIZE - 170

    # kline_helper.export_csv(data, filename=f"{TOKEN}_ce.csv")

    time.sleep(1)
    while True:
        counter += 1
        data_temp_dict = init_data()
        two_latest_klines = binance_spot.klines(PAIR, TIME_FRAME, limit=2)

        kline_helper.get_heikin_ashi(
            data_temp_dict,
            two_latest_klines,
            prev_item={
                "Open": data["Open"][SIZE - 3],
                "Close": data["Close"][SIZE - 3],
                "High": data["High"][SIZE - 3],
                "Low": data["Low"][SIZE - 3],
            },
        )

        print(f"Time: {counter} {_token} {data_temp_dict['Time1'][0]}, {data_temp_dict['Time1'][1]}")

        if timestamp == data_temp_dict["Time"][1]:
            df_temp = chandelier_exit_2.calculate_atr(pd.DataFrame(data_temp_dict))
            data_temp_dict["ATR"] = df_temp["ATR"].values.tolist()

            # Save 3rd last direction
            chandelier_exit.direction = data["Direction"][SIZE - 3]

            # Remove 2 last data
            kline_helper._pop_tail_data(data)
            kline_helper._pop_tail_data(data)

            # Append new data
            kline_helper._append_data(data, data_temp_dict)

            # Calculate Chandelier Exit for Data
            chandelier_exit.calculate_chandelier_exit(data)

            # Save to CSV
            # kline_helper.export_csv(data, filename=f"{TOKEN}_ce.csv")

        elif timestamp == data_temp_dict["Time"][0]:
            timestamp = data_temp_dict["Time"][1]
            hasSentSignal = False

            kline_helper._pop_top_data(data)

            df_temp = chandelier_exit_2.calculate_atr(pd.DataFrame(data_temp_dict))
            data_temp_dict["ATR"] = df_temp["ATR"].values.tolist()

            # Save 2nd last direction
            chandelier_exit.direction = data["Direction"][SIZE - 2]

            # Remove 1 last data
            kline_helper._pop_tail_data(data)

            # Append new data
            kline_helper._append_data(data, data_temp_dict)

            # Calculate Chandelier Exit for Data
            chandelier_exit.calculate_chandelier_exit(data)

            # Save to CSV
            # kline_helper.export_csv(data, filename=f"{TOKEN}_ce.csv")

        else:
            Exception("Time not match !!!")
            break

        if data["Direction"][SIZE - 2] != data["Direction"][SIZE - 3]:
            if not hasSentSignal:
                signal = "SELL" if data["Direction"][SIZE - 1] == -1 else "BUY"
                prev_open_price = data["Open_p"][SIZE - 2]
                prev_close_price = data["Close_p"][SIZE - 2]
                per = (prev_close_price - prev_open_price) / prev_open_price * 100
                per = per > 0 and f"+{per:.3f}%" or f"{per:.3f}%"
                body = {
                    "signal": signal,
                    "symbol": f"${TOKEN}",
                    "time_frame": TIME_FRAME,
                    "time": data["Time1"][SIZE - 1][11:],
                    "price": data["Close"][SIZE - 1],
                    "change": per,
                }
                send_telegram_message(body)
                hasSentSignal = True
                print(f"Signal sent:", body)
        time.sleep(TIME_SLEEP)


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
        "Direction",
        "Open_p",
        "Close_p",
    ]

    data = {key: [] for key in keys}
    return data


import multiprocessing


def run_strategy(token, time_frame, pair, TIME_SLEEP):
    while True:
        try:
            print("STARTING CE BOT")
            data = init_data()
            main(data, token, time_frame, pair, TIME_SLEEP)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    # Set up argparse to handle command-line arguments
    parser = argparse.ArgumentParser(description="Process trading pair and timeframe.")
    parser.add_argument("--timeframe", type=str, help='Time frame, e.g., "1m"', default="1m")
    parser.add_argument("--sleep", type=str, help='Time sleep, e.g., "15"', default="10")

    # Parse arguments
    args = parser.parse_args()
    TIME_FRAME = args.timeframe
    TIME_SLEEP = int(args.sleep)

    # Reading the tokens from the file
    with open("tokens.txt", "r") as file:
        tokens = [line.strip() for line in file]

    strategies = [(token, TIME_FRAME, f"{token}USDT") for token in tokens]

    processes = []
    for token, time_frame, pair in strategies:
        process = multiprocessing.Process(target=run_strategy, args=(token, time_frame, pair, TIME_SLEEP))
        processes.append(process)
        process.start()
