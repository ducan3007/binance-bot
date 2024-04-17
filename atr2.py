import pandas as pd
import numpy as np
from ta.volatility import AverageTrueRange
from binance.spot import Spot
from datetime import datetime, timezone, timedelta
import time

client = Spot()

SIZE = 250
LENGTH = 1
MULT = 2
USE_CLOSE = True
DIRECTION = 1

time_frame = {
    "5m": 300000,
    "15m": 900000,
}


def append_data(data, klines):
    for kline in klines:
        data["Open"].append(float(kline[1]))
        data["High"].append(float(kline[2]))
        data["Low"].append(float(kline[3]))
        data["Close"].append(float(kline[4]))
        # to local time
        data["Time"].append(kline[0])

        data["ATR"].append(None)
        data["LongStop"].append(None)
        data["ShortStop"].append(None)
        data["LongStopPrev"].append(None)
        data["ShortStopPrev"].append(None)
        data["Direction"].append(None)


def calculate_atr(df, length=1, multiplier=2):
    atr_calculator = AverageTrueRange(df["High"], df["Low"], df["Close"], window=length)
    df["ATR"] = atr_calculator.average_true_range() * multiplier
    return df


def calculate_chandelier_exit(data, length=1, multiplier=2, use_close=True):
    global DIRECTION
    for i in range(SIZE):
        """
        LONGSTOP
        """
        if data["LongStop"][i] and data["LongStopPrev"][i] and data["ShortStop"][i] and data["ShortStopPrev"][i]:
            continue
        else:
            print("Calculating Chandelier Exit", data["Time"][i])

        longStop = (
            max(data["Close"][max(0, i - length + 1) : i + 1])
            if use_close
            else max(data["High"][max(0, i - length + 1) : i + 1])
        ) - data["ATR"][i]

        longStopPrev = data["LongStop"][i - 1] if data["LongStop"][i - 1] is not None else longStop

        if data["Close"][i - 1] > longStopPrev:
            longStop = max(longStop, longStopPrev)
        else:
            longStop = longStop

        data["LongStop"][i] = longStop
        data["LongStopPrev"][i] = longStopPrev

        shortStop = (
            min(data["Close"][max(0, i - length + 1) : i + 1])
            if use_close
            else min(data["Low"][max(0, i - length + 1) : i + 1])
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
    klines = client.klines(
        "SOLUSDT",
        "5m",
        limit=SIZE,
    )
    append_data(klines, data)
    dfdata = pd.DataFrame(data)
    dfresult = calculate_atr(dfdata, LENGTH, MULT)
    data["ATR"] = dfresult["ATR"]
    calculate_chandelier_exit(data, LENGTH, MULT, USE_CLOSE)

    while True:
        klines = client.klines(
            "SOLUSDT",
            "15m",
            limit=1,
        )
        pop_data(data)
        append_data(data, klines)
        dfdata = pd.DataFrame(data)
        dfresult = calculate_atr(dfdata, LENGTH, MULT)

        # Sleep for 10 seconds
        df_result[["Time", "Direction", "Close", "ShortStopPrev", "LongStopPrev"]].to_csv("atr2.csv", index=False)
        time.sleep(10)


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
    print(time.mktime(datetime.now().timetuple()) * 1000)

    # save to atr2.csv
