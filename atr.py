import pandas as pd
import numpy as np
from ta.volatility import AverageTrueRange
from binance.spot import Spot
from datetime import datetime, timezone, timedelta

client = Spot()
SIZE = 200

sol_usdt_klines = client.klines(
    "SOLUSDT",
    "15m",
    limit=SIZE,
)


def parse_klines(klines):
    data = {
        "Open": [],
        "High": [],
        "Low": [],
        "Close": [],
        "Time": [],
    }

    for kline in klines:
        data["Open"].append(float(kline[1]))
        data["High"].append(float(kline[2]))
        data["Low"].append(float(kline[3]))
        data["Close"].append(float(kline[4]))
        data["Time"].append(
            datetime.fromtimestamp(kline[0] / 1000)
            .astimezone()
            .strftime("%Y-%m-%d %H:%M:%S")
        )
    return data


# Input data
data = parse_klines(sol_usdt_klines)

df = pd.DataFrame(data)
df.to_csv("atr_day.csv", index=False)

# Configuration
length = 1  # ATR period
mult = 2  # ATR multiplier
useClose = True  # Using close prices for extremums

# Calculate ATR
atr_calculator = AverageTrueRange(df["High"], df["Low"], df["Close"], window=length)
df["ATR"] = atr_calculator.average_true_range() * mult


if useClose:
    df["highest"] = df["Close"].rolling(window=length).max()
    df["lowest"] = df["Close"].rolling(window=length).min()
else:
    df["highest"] = df["High"].rolling(window=length).max()
    df["lowest"] = df["Low"].rolling(window=length).min()

# Initial longStop and shortStop calculation
df["longStop"] = df["highest"] - df["ATR"]
df["longStopPrev"] = df["longStop"].shift(1).fillna(df["longStop"])
df["longStop"] = np.where(
    df["Close"].shift(1) > df["longStopPrev"],
    np.maximum(df["longStop"], df["longStopPrev"]),
    df["longStop"],
)


df["shortStop"] = df["lowest"] + df["ATR"]
df["shortStopPrev"] = df["shortStop"].shift(1).fillna(df["shortStop"])
df["shortStop"] = np.where(
    df["Close"].shift(1) < df["shortStopPrev"],
    np.minimum(df["shortStop"], df["shortStopPrev"]),
    df["shortStop"],
)

print(
    df[
        [
            "Time",
            "Close",
            "ATR",
            "highest",
            "lowest",
            "longStopPrev",
            "shortStopPrev",
            "longStop",
            "shortStop",
        ]
    ]
)

# save to csv
df.to_csv("atr.csv", index=False)
