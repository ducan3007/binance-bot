# Description: This script is used to backtest the Chandelier Exit strategy on Binance Futures.

import time
import pandas as pd
from ta.trend import WMAIndicator, EMAIndicator
from binance.spot import Spot
from enum import Enum
from datetime import datetime, timedelta
import requests
import json
import numpy as np

EPSILON = 1e-9

NON_SPOT_PAIRS = {
    "TONUSDT": "TONUSDT",
    "ONDOUSDT": "ONDOUSDT",
}

# Define the maximum number of klines per request
MAX_KLINES = 1000


class CEConfig(Enum):
    SIZE = 200
    LENGTH = 1
    MULT = 2.0
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
        """
        real_price_* : Real price of the candle, not Heikin Ashi
        """

        data["real_price_open"].append(open_p)
        data["real_price_close"].append(close_p)

        if len(data["real_price_close"]) > 1:  # Ensure there's a previous Close price to compare
            prev_close_price = data["real_price_close"][-2]
            change = (close_p - prev_close_price) / prev_close_price * 100
        else:
            change = None
        data["real_price_change"].append(change)

    def get_heikin_ashi(self, data, klines, prev_item=None):
        for kline in klines:
            self._append_heikin_ashi(data, kline, prev_item)

    def export_csv(self, dfdata, filename="atr2.csv"):
        dfdata[["Time1", "MHULL", "SHULL", "hull_color"]].to_csv(filename)

    def fetch_klines_non_spot(PAIR, TIME_FRAME, startTimeMs, endTimeMs, limit):
        URL = f"https://fapi.binance.com/fapi/v1/klines?symbol={PAIR}&interval={TIME_FRAME}&startTime={startTimeMs}&endTime={endTimeMs}&limit={limit}"
        headers = {"Content-Type": "application/json"}
        res = requests.get(URL, headers=headers, timeout=None)
        return res.json()

    def fetch_klines(self, binance_spot: Spot, PAIR, TIME_FRAME, startTimeMs, endTimeMs, limit):
        if PAIR in NON_SPOT_PAIRS:
            return self.fetch_klines_non_spot(PAIR, TIME_FRAME, startTimeMs, endTimeMs, limit)
        return binance_spot.klines(PAIR, TIME_FRAME, limit=limit, startTime=startTimeMs, endTime=endTimeMs)

    def fetch_klines_by_date_range(self, binance_spot: Spot, PAIR, TIME_FRAME, start_date_str=None, end_date_str=None):
        if end_date_str:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        else:
            end_date = datetime.utcnow()

        if start_date_str:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        else:
            start_date = end_date - timedelta(days=1)

        startTimeMs = int(start_date.timestamp() * 1000)
        endTimeMs = int((end_date + timedelta(days=1)).timestamp() * 1000)

        klines = []
        current_start_time = startTimeMs

        while current_start_time < endTimeMs:
            # Calculate the next end time for the request
            next_end_time = min(
                current_start_time + MAX_KLINES * self.get_milliseconds(TIME_FRAME),
                endTimeMs,
            )
            data = self.fetch_klines(
                binance_spot,
                PAIR,
                TIME_FRAME,
                current_start_time,
                next_end_time,
                MAX_KLINES,
            )
            klines.extend(data)
            current_start_time = int(data[-1][0]) + self.get_milliseconds(TIME_FRAME)  # Move to the next kline start time
        return klines

    def get_milliseconds(self, time_frame):
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


class HullSuite:
    def __init__(
        self,
        data,
        mode="Hma",
        length=55,
        length_mult=1.0,
        use_htf=False,
        htf="240",
        switch_color=True,
        candle_col=False,
        visual_switch=True,
        thickness_switch=1,
        transp_switch=40,
    ):
        self.data = data
        self.mode = mode
        self.length = length
        self.length_mult = length_mult
        self.use_htf = use_htf
        self.htf = htf
        self.switch_color = switch_color
        self.candle_col = candle_col
        self.visual_switch = visual_switch
        self.thickness_switch = thickness_switch
        self.transp_switch = transp_switch

    def HMA(self, length):
        half_length = length // 2
        sqrt_length = int(np.sqrt(length))
        wmaf = WMAIndicator(self.data["Close"], window=half_length).wma()
        wmas = WMAIndicator(self.data["Close"], window=length).wma()
        return WMAIndicator(2 * wmaf - wmas, window=sqrt_length).wma()

    def EHMA(self, length):
        half_length = length // 2
        sqrt_length = int(np.sqrt(length))
        emaf = EMAIndicator(self.data["Close"], window=half_length).ema_indicator()
        emas = EMAIndicator(self.data["Close"], window=length).ema_indicator()
        return EMAIndicator(2 * emaf - emas, window=sqrt_length).ema_indicator()

    def THMA(self, length):
        length3 = length // 3
        length2 = length // 2
        wma1 = WMAIndicator(self.data["Close"], window=length3).wma() * 3
        wma2 = WMAIndicator(self.data["Close"], window=length2).wma()
        wma3 = WMAIndicator(self.data["Close"], window=length).wma()
        return WMAIndicator(wma1 - wma2 - wma3, window=length).wma()

    def mode_switch(self, mode, length):
        if mode == "Hma":
            return self.HMA(length)
        elif mode == "Ehma":
            return self.EHMA(length)
        elif mode == "Thma":
            return self.THMA(length)
        else:
            return None

    def calculate_hull(self):
        _hull = self.mode_switch(self.mode, int(self.length * self.length_mult))

        if self.use_htf:
            # Higher timeframe logic can be implemented here if needed
            HULL = _hull  # Simplified for this example
        else:
            HULL = _hull

        self.data["MHULL"] = HULL
        self.data["SHULL"] = HULL.shift(2)

        if self.switch_color:
            self.data["hull_color"] = np.where(self.data["MHULL"] > self.data["SHULL"], "green", "red")
        else:
            self.data["hull_color"] = "white"

        if self.candle_col:
            self.data["bar_color"] = self.data["hull_color"]

        return self.data


data = {
    "Open": [],
    "High": [],
    "Low": [],
    "Close": [],
    "Time1": [],
    "Time": [],
    "real_price_open": [],
    "real_price_close": [],
    "real_price_change": [],
}

PAIR = "BTCUSDT"
TIME_FRAME = "15m"
KlineHelper = KlineHelper()
binance_spot = Spot()

klines = KlineHelper.fetch_klines_by_date_range(
    binance_spot,
    PAIR,
    TIME_FRAME,
    start_date_str=f"2024-06-01",
    end_date_str=f"2024-07-12",
)
KlineHelper.get_heikin_ashi(data, klines)


pdData = pd.DataFrame(data)


hull_suite = HullSuite(
    data=pdData,
    mode="Hma",
    length=50,
    length_mult=1.0,
    use_htf=False,
    htf="240",
    switch_color=True,
    candle_col=False,
    visual_switch=True,
    thickness_switch=1,
    transp_switch=40,
)

result = hull_suite.calculate_hull()
KlineHelper.export_csv(result, "hull_suite.csv")
