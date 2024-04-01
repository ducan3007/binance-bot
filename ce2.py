import pandas as pd
import numpy as np
from ta.volatility import AverageTrueRange

data = [
    # High, Low, Close, ATR, Long Stop, Short Stop
    [176.72, 175.54, 175.82],
    [176.11, 174.60, 174.82],
    [175.95, 174.53, 175.61],
]


LENGTH = 1
MULT = 2
USE_CLOSE = True


# Function to calculate True Range
def true_range(high, low, prev_close):
    tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
    return tr


# Function to calculate ATR for each row in data
def add_atr_to_data(data, length=LENGTH, mult=MULT):
    tr_values = []
    atr_values = []
    for i in range(len(data)):
        high, low, close = data[i]
        if i == 0:
            tr = high - low
        else:
            prev_close = data[i - 1][2]
            tr = true_range(high, low, prev_close)
        tr_values.append(tr)
    for i in range(len(tr_values)):
        if i < length:  # Not enough data to fill the length requirement
            atr = sum(tr_values[: i + 1]) / (i + 1)
        else:
            atr = sum(tr_values[i - length + 1 : i + 1]) / length
        atr_values.append(round(atr * mult, 2))

    # loop backwards
    for i, row in enumerate(data):
        row.append(atr_values[i])
        long_stop = max(data[i - length + 1 : i + 1]) - atr_values[i]
        long_stop_prev = data[i - 1][4] if data[i - 1][4] else long_stop
        if data[i - 1][2] > long_stop_prev:
            long_stop = max(data[i - 1][4], long_stop_prev)

    return data


print(add_atr_to_data(data))


data = [ 1, 2 , 3, 4, 5, 6, 7, 8, 9, 10]
i = 4
length = 1
print(data[i - length + 1 : i + 1])