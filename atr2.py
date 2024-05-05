import time
import pandas as pd
from ta.volatility import AverageTrueRange
from binance.spot import Spot
from enum import Enum
from datetime import datetime
from io import StringIO
import requests
import json

binance_spot = Spot()

DIRECTION = 1


class CEConfig(Enum):
    SIZE = 100
    LENGTH = 1
    MULT = 2
    USE_CLOSE = True
    SUB_SIZE = 2


class TradePair(str, Enum):
    SOL_USDT = "SOLUSDT"
    BTC_USDT = "BTCUSDT"
    ETH_USDT = "ETHUSDT"
    NEAR_USDT = "NEARUSDT"
    JTO_USDT = "JTOUSDT"
    TAO_USDT = "TAOUSDT"
    BONK_USDT = "BONKUSDT"
    DOGE_USDT = "DOGEUSDT"


class Coin(str, Enum):
    SOLUSDT = "SOL"
    BTCUSDT = "BTC"
    ETHUSDT = "ETH"
    NEARUSDT = "NEAR"
    JTOUSDT = "JTO"
    TAOUSDT = "TAO"
    BONKUSDT = "BONK"
    DOGEUSDT = "DOGE"


class TIME_FRAME_STR(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"


class TIME_FRAME_MS(int, Enum):
    M5 = 5 * 60
    M15 = 15 * 60
    H1 = 60 * 60


TOKEN = TradePair.DOGE_USDT
TIME_FRAME = TIME_FRAME_STR.M1


class KlineHelper:
    def _append_klines(self, data, kline):
        data["Open"].append(float(kline[1]))
        data["High"].append(float(kline[2]))
        data["Low"].append(float(kline[3]))
        data["Close"].append(float(kline[4]))
        data["Time"].append(datetime.fromtimestamp(int(kline[0]) / 1000).strftime("%Y-%m-%d %H:%M:%S"))
        # data["Time"].append(int(kline[0]) / 1000)
        data["ATR"].append(None)
        data["LongStop"].append(None)
        data["ShortStop"].append(None)
        data["LongStopPrev"].append(None)
        data["ShortStopPrev"].append(None)
        data["Direction"].append(None)

    def _pop_tail_data(self, data):
        for key in data:
            data[key].pop()

    def _pop_top_data(self, data):
        for key in data:
            data[key].pop(0)

    def _append_data(self, data1, data2):
        for key in data1:
            data1[key].extend(data2[key])

    def update_data(self, data, klines):
        for kline in klines:
            self._append_klines(data, kline)

    def export_csv(self, data, filename="atr2.csv"):
        dfdata = pd.DataFrame(data)
        output = StringIO()
        dfdata[["Time", "Direction", "Close", "LongStop", "ShortStop"]].to_csv(
            output, index=False, float_format="%.8f", sep=" "
        )
        csv_string = output.getvalue()
        with open(filename, "w") as f:
            f.write(csv_string)


class ChandlierExit:
    def __init__(self, size, multiplier=2, length=1, use_close=True):
        self.size = size
        self.length = length
        self.use_close = use_close
        self.multiplier = multiplier

    def calculate_atr(self, df):
        atr_calculator = AverageTrueRange(df["High"], df["Low"], df["Close"], window=self.length)
        df["ATR"] = atr_calculator.average_true_range() * self.multiplier
        return df

    def calculate_chandelier_exit(self, data):
        global DIRECTION
        for i in range(self.size):
            if data["LongStop"][i] and data["LongStopPrev"][i] and data["ShortStop"][i] and data["ShortStopPrev"][i]:
                continue
            else:
                pass

            longStop = (
                max(data["Close"][max(0, i - self.length + 1) : i + 1])
                if self.use_close
                else max(data["High"][max(0, i - self.length + 1) : i + 1])
            ) - data["ATR"][i]

            longStopPrev = data["LongStop"][i - 1] if data["LongStop"][i - 1] is not None else longStop

            if data["Close"][i - 1] > longStopPrev:
                longStop = max(longStop, longStopPrev)
            else:
                longStop = longStop

            data["LongStop"][i] = longStop
            data["LongStopPrev"][i] = longStopPrev

            shortStop = (
                min(data["Close"][max(0, i - self.length + 1) : i + 1])
                if self.use_close
                else min(data["Low"][max(0, i - self.length + 1) : i + 1])
            ) + data["ATR"][i]

            shortStopPrev = data["ShortStop"][i - 1] if data["ShortStop"][i - 1] is not None else shortStop

            if data["Close"][i - 1] < shortStopPrev:
                shortStop = min(shortStop, shortStopPrev)
            else:
                shortStop = shortStop

            data["ShortStop"][i] = shortStop
            data["ShortStopPrev"][i] = shortStopPrev

            dir = 1

            if data["Close"][i] > data["ShortStopPrev"][i]:
                DIRECTION = 1
                dir = 1
            elif data["Close"][i] < data["LongStopPrev"][i]:
                DIRECTION = -1
                dir = -1
            else:
                dir = DIRECTION

            data["Direction"][i] = dir


def send_telegram_message(body):
    URL = "http://localhost:8000/sendMessage"
    headers = {"Content-Type": "application/json"}
    requests.post(URL, headers=headers, data=json.dumps(body))


def main(data):
    (SIZE, LENGTH, MULT, USE_CLOSE, SUB_SIZE) = (
        CEConfig.SIZE.value,
        CEConfig.LENGTH.value,
        CEConfig.MULT.value,
        CEConfig.USE_CLOSE.value,
        CEConfig.SUB_SIZE.value,
    )
    print(f"Starting {TOKEN}: SIZE: {SIZE}, LENGTH: {LENGTH}, MULT: {MULT}, USE_CLOSE: {USE_CLOSE}")

    kline_helper = KlineHelper()
    chandelier_exit = ChandlierExit(size=SIZE, length=LENGTH, multiplier=MULT, use_close=USE_CLOSE)

    # Get 500 Klines
    klines = binance_spot.klines(TOKEN, TIME_FRAME, limit=SIZE)
    kline_helper.update_data(data, klines)
    df_data = pd.DataFrame(data)

    # Calculate ATR
    df_result = chandelier_exit.calculate_atr(df=df_data)

    # Update ATR to data
    data["ATR"] = df_result["ATR"].values.tolist()

    # Calculate Chandelier Exit
    chandelier_exit.calculate_chandelier_exit(data=data)

    kline_helper.export_csv(data)

    # Save the last time, [700, 1000, 1300]
    timestamp = data["Time"][SIZE - 1]
    hasSentSignal = False

    time.sleep(1)

    chandelier_exit_2 = ChandlierExit(size=SUB_SIZE, length=LENGTH, multiplier=MULT, use_close=USE_CLOSE)
    counter = 0

    while True:
        counter += 1
        data_temp_dict = init_data()

        two_latest_klines = binance_spot.klines(TOKEN, TIME_FRAME, limit=2)
        kline_helper.update_data(data_temp_dict, two_latest_klines)

        print(f"Time: {counter} {data_temp_dict['Time'][0]}, {data_temp_dict['Time'][1]}")

        if timestamp == data_temp_dict["Time"][1]:  # [1000, 1300]
            df_temp = chandelier_exit_2.calculate_atr(pd.DataFrame(data_temp_dict))
            data_temp_dict["ATR"] = df_temp["ATR"].values.tolist()

            # Remove 2 last data
            kline_helper._pop_tail_data(data)
            kline_helper._pop_tail_data(data)

            # Append new data
            kline_helper._append_data(data, data_temp_dict)

            # Calculate Chandelier Exit for Data
            chandelier_exit.calculate_chandelier_exit(data)

        elif timestamp == data_temp_dict["Time"][0]:  # [700, 1000]
            timestamp = data_temp_dict["Time"][1]
            hasSentSignal = False

            kline_helper._pop_top_data(data)
            df_temp = chandelier_exit_2.calculate_atr(pd.DataFrame(data_temp_dict))
            data_temp_dict["ATR"] = df_temp["ATR"].values.tolist()

            # Remove 1 last data
            kline_helper._pop_tail_data(data)

            # Append new data
            kline_helper._append_data(data, data_temp_dict)

            # Calculate Chandelier Exit for Data
            chandelier_exit.calculate_chandelier_exit(data)

        else:
            Exception("Time not match !!!")
            break

        if data["Direction"][SIZE - 1] != data["Direction"][SIZE - 2] and not hasSentSignal:
            body = {
                "signal": "SELL" if data["Direction"][SIZE - 1] == -1 else "BUY",
                "symbol": Coin[TOKEN.value].value,
                "time_frame": TIME_FRAME,
                "price": data["Close"][SIZE - 1],
            }
            send_telegram_message(body)
            hasSentSignal = True

        time.sleep(10)


def init_data():
    keys = [
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
        "Direction",
    ]

    data = {key: [] for key in keys}
    return data


if __name__ == "__main__":
    data = init_data()

    while True:
        try:
            main(data)
        except Exception as e:
            print(f"Error: {e}", "Restarting after 10 seconds...")
            time.sleep(10)
