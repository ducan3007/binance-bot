import numpy as np
import pandas as pd
import requests
from datetime import datetime


# Helper class to append kline data
class KlineHelper:
    def __init__(self, mode, exchange):
        self.mode = mode
        self.exchange = exchange

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
        data["Direction"].append(None)
        data["Open_p"].append(open_p)
        data["Close_p"].append(close_p)

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
        data["Direction"].append(None)
        data["Open_p"].append(open_p)
        data["Close_p"].append(close_p)

    def populate(self, data, klines, prev_item=None):
        for kline in klines:
            if self.mode == "heikin_ashi":
                self._append_heikin_ashi(data, kline, prev_item)
            else:
                self._append_kline(data, kline)

    def export_csv(self, data, filename="atr2.csv"):
        dfdata = pd.DataFrame(data)
        # dfdata[["Time1", "ZLSMA_34", "ZLSMA_50"]].to_csv(filename)
        dfdata.to_csv(filename)


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
        "Direction",
        "Open_p",
        "Close_p",
    ]

    data = {key: [] for key in keys}
    return data


# Fetch historical Kline data from Binance and convert to the data structure
def fetch_binance_klines(PAIR="BTCUSDT", TIME_FRAME="1h", limit=320):
    URL = f"https://fapi.binance.com/fapi/v1/klines?symbol={PAIR}&interval={TIME_FRAME}&limit={limit}"
    headers = {"Content-Type": "application/json"}
    res = requests.get(URL, headers=headers, timeout=None)
    klines = res.json()

    return klines


def calculate_zlsma(data, key="ZLSMA", length=32, offset=0):
    # Extract closing prices from the data structure
    close_prices = np.array(data["Close"], dtype=float)

    zlsma = ZLSMA(close_prices, length, offset)

    # Add ZLSMA to the data structure
    data[key] = zlsma.tolist()


def fetch_zlsma(PAIR, TIME_FRAME):
    klines = fetch_binance_klines(PAIR, TIME_FRAME, 320)

    data = init_data()
    helper = KlineHelper(mode="heikin_ashi", exchange="future")
    helper.populate(data, klines)
    # Calculate ZLSMA
    calculate_zlsma(data, "ZLSMA_34", 34, 0)
    calculate_zlsma(data, "ZLSMA_50", 50, 0)

    data_pdf = pd.DataFrame(data)

    # remove first 120 rows
    data_pdf = data_pdf.iloc[220:]
    # resset index
    data_pdf.reset_index(drop=True, inplace=True)
    # helper.export_csv(data_pdf, filename="zlma.csv")
    
    return data_pdf
