import pandas as pd
import numpy as np
from ta.volatility import AverageTrueRange
from binance.spot import Spot
from datetime import datetime, timezone, timedelta

client = Spot()

SIZE = 500
LENGTH = 1
MULT = 2
USE_CLOSE = True

sol_usdt_klines = client.klines(
    "SOLUSDT",
    "15m",
    limit=SIZE,
)

data = {
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
}


def parse_klines(klines):

    for kline in klines:
        data["Open"].append(float(kline[1]))
        data["High"].append(float(kline[2]))
        data["Low"].append(float(kline[3]))
        data["Close"].append(float(kline[4]))
        # to local time
        data["Time"].append(
            datetime.fromtimestamp(kline[0] / 1000)
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S")
        )

        data["ATR"].append(None)
        data["LongStop"].append(None)
        data["ShortStop"].append(None)
        data["LongStopPrev"].append(None)
        data["ShortStopPrev"].append(None)

    return pd.DataFrame(data)


def calculate_atr(df, length=1, multiplier=2):
    atr_calculator = AverageTrueRange(df["High"], df["Low"], df["Close"], window=length)
    df["ATR"] = atr_calculator.average_true_range() * multiplier
    return df


def calculate_chandelier_exit(data, length=1, multiplier=2, use_close=True):
    for i in range(SIZE):
        """
        LONGSTOP
        """
        longStop = (
            max(data["Close"][max(0, i - length + 1) : i + 1])
            if use_close
            else max(data["High"][max(0, i - length + 1) : i + 1])
        ) - data["ATR"][i]

        longStopPrev = (
            data["LongStop"][i - 1] if data["LongStop"][i - 1] is not None else longStop
        )

        if data["Close"][i - 1] > longStopPrev:
            longStop = max(longStop, longStopPrev)
        else:
            longStop = longStop

        data["LongStop"][i] = longStop
        data["LongStopPrev"][i] = longStopPrev

        """
        SHORTSTOP
        """

        shortStop = (
            min(data["Close"][max(0, i - length + 1) : i + 1])
            if use_close
            else min(data["Low"][max(0, i - length + 1) : i + 1])
        ) + data["ATR"][i]

        shortStopPrev = (
            data["ShortStop"][i - 1]
            if data["ShortStop"][i - 1] is not None
            else shortStop
        )

        if data["Close"][i - 1] < shortStopPrev:
            shortStop = min(shortStop, shortStopPrev)
        else:
            shortStop = shortStop

        data["ShortStop"][i] = shortStop
        data["ShortStopPrev"][i] = shortStopPrev


def main():
    dfdata = parse_klines(sol_usdt_klines)
    dfresult = calculate_atr(dfdata, LENGTH, MULT)
    data["ATR"] = dfresult["ATR"]
    calculate_chandelier_exit(data, LENGTH, MULT, USE_CLOSE)


if __name__ == "__main__":
    main()


df_result = pd.DataFrame(data)

print(
    df_result[["Time", "ATR", "LongStop", "ShortStop", "LongStopPrev", "ShortStopPrev"]]
)

# save to atr2.csv

df_result[["Time", "ATR", "LongStop", "ShortStop", "LongStopPrev", "ShortStopPrev"]].to_csv("atr2.csv", index=False)