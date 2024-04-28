import pandas as pd
import numpy as np
from ta.volatility import AverageTrueRange
from binance.spot import Spot
from datetime import datetime, timezone, timedelta
from enum import Enum
import time

client = Spot()

DIRECTION = 1


class CEConfig(Enum):
    SIZE = 250
    LENGTH = 1
    MULT = 2
    USE_CLOSE = True


class Token(str, Enum):
    SOL_USDT = "SOLUSDT"
    BTC_USDT = "BTCUSDT"
    ETH_USDT = "ETHUSDT"
    NEAR_USDT = "NEARUSDT"
    JTO_USDT = "JTOUSDT"
    TAO_USDT = "TAOUSDT"


class TIME_FRAME(str, Enum):
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"


class TIME_FRAME_MS(int, Enum):
    M5 = 5 * 60
    M15 = 15 * 60
    H1 = 60 * 60


class KlineHelper:
    def _append_data(self, data, kline):
        data["Open"].append(float(kline[1]))
        data["High"].append(float(kline[2]))
        data["Low"].append(float(kline[3]))
        data["Close"].append(float(kline[4]))
        # data["Time"].append(datetime.fromtimestamp(int(kline[0]) / 1000).strftime("%Y-%m-%d %H:%M:%S"))
        data["Time"].append(int(kline[0]) / 1000)
        data["ATR"].append(None)
        data["LongStop"].append(None)
        data["ShortStop"].append(None)
        data["LongStopPrev"].append(None)
        data["ShortStopPrev"].append(None)
        data["Direction"].append(None)

    def _pop_tail_data(data):
        for key in data:
            data[key].pop()

    def _pop_top_data(data):
        for key in data:
            data[key].pop(0)

    def update_data(self, data, klines):
        for kline in klines:
            self._append_data(data, kline)

    def export_csv(self, data):
        dfdata = pd.DataFrame(data)
        dfdata[["Time", "Direction", "LongStop", "ShortStop"]].to_csv("atr2.csv", index=False)


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
                print("Calculating Chandelier Exit", data["Time"][i])

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


def main(data):
    (SIZE, LENGTH, MULT, USE_CLOSE) = (
        CEConfig.SIZE.value,
        CEConfig.LENGTH.value,
        CEConfig.MULT.value,
        CEConfig.USE_CLOSE.value,
    )
    print(f"Starting BOT: SIZE: {SIZE}, LENGTH: {LENGTH}, MULT: {MULT}, USE_CLOSE: {USE_CLOSE}")
    klines = client.klines(
        Token.SOL_USDT,
        TIME_FRAME.M5,
        limit=SIZE,
    )
    kline = KlineHelper()
    chandelier_exit = ChandlierExit(size=SIZE, length=LENGTH, multiplier=MULT, use_close=USE_CLOSE)
    kline.update_data(
        data,
        klines,
    )
    dfdata = pd.DataFrame(data)
    dfresult = chandelier_exit.calculate_atr(df=dfdata)
    data["ATR"] = dfresult["ATR"]
    chandelier_exit.calculate_chandelier_exit(data=data)
    kline.export_csv(data)
    current_time_sec = data["Time"][SIZE - 1]
    print(f"Current Time: {current_time_sec}")

    while True:
        klines = client.klines(
            Token.SOL_USDT,
            TIME_FRAME.M5,
            limit=2,
        )
        data_chunk = kline.update_data(data, klines)
        if data_chunk["Time"][0] == current_time_sec:
            dfdata = pd.DataFrame(data)
            dfresult = chandelier_exit.calculate_atr(df=dfdata)
            data["ATR"] = dfresult["ATR"]
            chandelier_exit.calculate_chandelier_exit(data=data)
            kline.export_csv(data)
            pop_data(data)
            time.sleep(6)

        time.sleep(6)


def pop_data(data):
    for key in data:
        data[key].pop()


if __name__ == "__main__":
    data_5m = {
        "Open": [],
        "High": [],
        "Low": [],
        "Close": [],
        "Time": [],
        "ATR": [],
        "LongStop": [],
        "ShortStop": [],
        "LongStopPrev": [],
        "ShortStopPrev": [],
        "Direction": [],
    }
    main(data_5m)
    df_result = pd.DataFrame(data_5m)
    print(
        df_result.tail(1)[
            ["Time", "ATR", "Close", "Direction", "LongStop", "ShortStop", "LongStopPrev", "ShortStopPrev"]
        ]
    )
    print("Done")
