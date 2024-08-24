import numpy as np
import pandas as pd
import requests
from datetime import datetime


# Helper class to append kline data
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

        if len(data["real_price_close"]) > 1:
            prev_close_price = data["real_price_close"][-2]
            change = (close_p - prev_close_price) / prev_close_price * 100
        else:
            change = None
        data["real_price_change"].append(change)

    def get_kline_data(self, data, klines, prev_item=None):
        for kline in klines:
            self._append_kline(data, kline)

    def export_csv(self, data, filename="atr2.csv"):
        dfdata = pd.DataFrame(data)
        dfdata[["Time1", "ZLSMA"]].to_csv(filename)


# Utility functions
def np_shift(array: np.ndarray, offset: int = 1, fill_value=np.nan):
    result = np.empty_like(array)
    if offset > 0:
        result[:offset] = fill_value
        result[offset:] = array[:-offset]
    elif offset < 0:
        result[offset:] = fill_value
        result[:offset] = array[-offset:]
    else:
        result[:] = array
    return result


def Linreg(source: np.ndarray, length: int, offset: int = 0):
    size = len(source)
    linear = np.zeros(size)

    for i in range(length, size):
        sumX = 0.0
        sumY = 0.0
        sumXSqr = 0.0
        sumXY = 0.0

        for z in range(length):
            val = source[i - z]
            per = z + 1.0
            sumX += per
            sumY += val
            sumXSqr += per * per
            sumXY += val * per

        slope = (length * sumXY - sumX * sumY) / (length * sumXSqr - sumX * sumX)
        average = sumY / length
        intercept = average - slope * sumX / length + slope

        linear[i] = intercept

    if offset != 0:
        linear = np_shift(linear, offset)

    return linear


def ZLSMA(source: np.ndarray, length: int, offset: int = 0):
    lsma = Linreg(source, length, offset)
    lsma2 = Linreg(lsma, length, offset)
    eq = lsma - lsma2
    zlsma = lsma + eq
    return zlsma


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


# Fetch historical Kline data from Binance and convert to the data structure
def fetch_binance_klines(PAIR="BTCUSDT", TIME_FRAME="1h", limit=500):
    URL = f"https://fapi.binance.com/fapi/v1/klines?symbol={PAIR}&interval={TIME_FRAME}&limit={limit}"
    headers = {"Content-Type": "application/json"}
    res = requests.get(URL, headers=headers, timeout=None)
    klines = res.json()

    data = init_data()
    helper = KlineHelper()
    helper.get_kline_data(data, klines)

    return data


def calculate_zlsma(data, length=32, offset=0):
    # Extract closing prices from the data structure
    close_prices = np.array(data["Close"], dtype=float)

    zlsma = ZLSMA(close_prices, length, offset)

    # Add ZLSMA to the data structure
    data["ZLSMA"] = zlsma.tolist()


def fetch_zlsma(Ticker, interval, limit):
    data = fetch_binance_klines(Ticker, interval, limit)

    # Calculate ZLSMA
    calculate_zlsma(data)

    # Output the ZLSMA values
    KlineHelper().export_csv(data, "zlsma.csv")


fetch_zlsma("BTCUSDT", "15m", 500)
