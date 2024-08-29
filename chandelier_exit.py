import time
import pandas as pd
from lib.volatility import AverageTrueRange
from binance.spot import Spot
from enum import Enum
from datetime import datetime
import requests
import json
import argparse
from logger import logger

EPSILON = 1e-9

NON_SPOT_PAIRS = {
    "TONUSDT": "TONUSDT",
    "ONDOUSDT": "ONDOUSDT",
    "1000PEPEUSDT": "1000PEPEUSDT",
    "1000BONKUSDT": "1000BONKUSDT",
    "1000RATSUSDT": "1000RATSUSDT",
    "1000FLOKIUSDT": "1000FLOKIUSDT",
    "MEWUSDT": "MEWUSDT",
    "ZETAUSDT": "ZETAUSDT",
}

TOKEN_SHORTCUT = {"1000PEPE": "PEPE", "1000BONK": "BONK", "1000RATS": "RATS", "1000SATS": "SATS", "1000FLOKI": "FLOKI"}

TIME_FRAME_MS = {
    "15m": 15 * 60,
    "5m": 5 * 60,
    "30m": 30 * 60,
}


class CEConfig(Enum):
    SIZE = 200
    LENGTH = 1
    MULT = 1.8
    USE_CLOSE = True
    SUB_SIZE = 2


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

    def get_heikin_ashi(self, data, klines, prev_item=None):
        for kline in klines:
            if self.mode == "heikin_ashi":
                self._append_heikin_ashi(data, kline, prev_item)
            else:
                self._append_kline(data, kline)

    def _pop_tail_data(self, data):
        for key in data:
            data[key].pop()

    def _pop_top_data(self, data):
        for key in data:
            data[key].pop(0)

    def _append_data(self, data1, data2):
        for key in data1:
            data1[key].extend(data2[key])

    def fetch_klines_future(self, PAIR, TIME_FRAME, limit, weight):
        try:
            URL = f"https://fapi.binance.com/fapi/v1/klines?symbol={PAIR}&interval={TIME_FRAME}&limit={limit}"
            headers = {"Content-Type": "application/json"}
            res = requests.get(URL, headers=headers, timeout=None)
            weight["m1"] = int(res.headers["x-mbx-used-weight-1m"])
            return res.json()
        except Exception as e:
            logger.error(f"Error Fetching Future Klines: {e}")
            raise e

    def fetch_klines(self, binance_spot: Spot, PAIR, TIME_FRAME, limit, weight):
        if self.exchange == "future":
            return self.fetch_klines_future(PAIR, TIME_FRAME, limit, weight)
        else:
            if PAIR in NON_SPOT_PAIRS:
                return self.fetch_klines_future(PAIR, TIME_FRAME, limit, weight)
            return binance_spot.klines(PAIR, TIME_FRAME, limit=limit)

    def export_csv(self, data, filename="atr2.csv"):
        dfdata = pd.DataFrame(data)
        dfdata[["Time1", "Direction", "Open_p", "Close_p"]].to_csv(filename, index=False, float_format="%.15f", sep=" ")


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

            if data["Close"][i - 1] - longStopPrev > EPSILON:
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

            if data["Close"][i - 1] - shortStopPrev < -EPSILON:
                shortStop = min(shortStop, shortStopPrev)
            else:
                shortStop = shortStop

            data["ShortStop"][i] = shortStop
            data["ShortStopPrev"][i] = shortStopPrev

            dir = self.direction

            if data["Close"][i] - data["ShortStopPrev"][i] > EPSILON:
                dir = 1
            elif data["Close"][i] - data["LongStopPrev"][i] < -EPSILON:
                dir = -1

            self.direction = dir
            data["Direction"][i] = dir


def main(data, TOKEN, TIME_FRAME, PAIR, TIME_SLEEP, MODE, EXCHANGE):
    (SIZE, LENGTH, MULT, USE_CLOSE, SUB_SIZE) = (
        CEConfig.SIZE.value,
        CEConfig.LENGTH.value,
        CEConfig.MULT.value,
        CEConfig.USE_CLOSE.value,
        CEConfig.SUB_SIZE.value,
    )

    weight = {"m1": 0}

    if not MODE:
        MODE = "heikin_ashi"

    if MODE == "normal":
        MULT = 1.80

    print(f"Starting {PAIR}: MODE: {MODE}, SIZE: {SIZE}, LENGTH: {LENGTH}, MULT: {MULT}, USE_CLOSE: {USE_CLOSE}")

    kline_helper = KlineHelper(mode=MODE, exchange=EXCHANGE)
    binance_spot = Spot()
    chandelier_exit = ChandlierExit(size=SIZE, length=LENGTH, multiplier=MULT, use_close=USE_CLOSE)

    # Get 500 Klines
    klines = kline_helper.fetch_klines(binance_spot, PAIR, TIME_FRAME, SIZE, weight)
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
    lastSentMessage = {"message_id": None, "Time": None, "Direction": None}
    _token = TOKEN.ljust(12)
    chandelier_exit_2 = ChandlierExit(size=SUB_SIZE, length=LENGTH, multiplier=MULT, use_close=USE_CLOSE)

    if TOKEN in TOKEN_SHORTCUT:
        TOKEN = TOKEN_SHORTCUT[TOKEN]

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
        two_latest_klines = kline_helper.fetch_klines(binance_spot, PAIR, TIME_FRAME, 2, weight)

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

        _per = cal_change(data_temp_dict["Close_p"][1], data_temp_dict["Close_p"][0])
        print(f"Time: {counter} {weight['m1']} {_token}  {_per} {data_temp_dict['Time1'][1]}")

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
            logger.info(
                f"Time not match: {TOKEN} ts: {timestamp} 0: {data_temp_dict['Time'][0]} 1: {data_temp_dict['Time'][1]}"
            )
            raise Exception("Time not match !!!")
            break

        if TIME_FRAME == "30m" or TIME_FRAME == "15m":
            """
            Pre send telegram message before candle close
            """
            if (
                lastSentMessage["message_id"] is not None
                and lastSentMessage["Direction"] != data["Direction"][SIZE - 1]
                and lastSentMessage["Time"] == timestamp - TIME_FRAME_MS[TIME_FRAME]
            ):
                __time = datetime.fromtimestamp(lastSentMessage["Time"]).strftime("%Y-%m-%d %H:%M")

                if MODE == "normal":
                    __body = {"time_frame": f"{TIME_FRAME}_normal", "message_id": str(lastSentMessage["message_id"])}
                else:
                    __body = {"time_frame": f"{TIME_FRAME}", "message_id": str(lastSentMessage["message_id"])}

                logger.info(f"Delete invalid message: Token: {TOKEN} {__body}, ts = {__time}")
                res = delete_message(__body)
                if res:
                    lastSentMessage["Time"] = None
                    lastSentMessage["message_id"] = None
                    lastSentMessage["Direction"] = None

            if data["Direction"][SIZE - 1] != data["Direction"][SIZE - 2]:
                if not hasSentSignal and pre_send_signal(timestamp, TIME_FRAME):
                    logger.info(f"Pre send signal: {TOKEN} {TIME_FRAME} {timestamp}")
                    signal = "SELL" if data["Direction"][SIZE - 1] == -1 else "BUY"
                    close_p = data["Close_p"][SIZE - 1]
                    prev_close_price = data["Close_p"][SIZE - 2]
                    per = _cal_change(close_p, prev_close_price)
                    _time = datetime.fromtimestamp(timestamp + TIME_FRAME_MS[TIME_FRAME]).strftime("%H:%M")
                    body = {
                        "signal": signal,
                        "symbol": f"${TOKEN}",
                        "time_frame": TIME_FRAME,
                        "time": _time,
                        "price": data["Close"][SIZE - 1],
                        "change": per,
                    }
                    if MODE == "normal":
                        body["time_frame"] = f"{TIME_FRAME}_normal"
                    res = send_telegram_message(body)
                    if res:
                        if res.get("message_id"):
                            lastSentMessage["Time"] = timestamp
                            lastSentMessage["message_id"] = res.get("message_id")
                            lastSentMessage["Direction"] = data["Direction"][SIZE - 1]
                        hasSentSignal = True
                        logger.info(f"Signal sent: {body}")
        elif data["Direction"][SIZE - 2] != data["Direction"][SIZE - 3]:
            if not hasSentSignal:
                signal = "SELL" if data["Direction"][SIZE - 1] == -1 else "BUY"
                pre_close_price = data["Close_p"][SIZE - 2]
                pre_pre_close_price = data["Close_p"][SIZE - 3]
                per = _cal_change(pre_close_price, pre_pre_close_price)
                body = {
                    "signal": signal,
                    "symbol": f"${TOKEN}",
                    "time_frame": TIME_FRAME,
                    "time": data["Time1"][SIZE - 1][11:],
                    "price": data["Close"][SIZE - 1],
                    "change": per,
                }
                if MODE == "normal":
                    body["time_frame"] = f"{TIME_FRAME}_normal"
                res = send_telegram_message(body)
                if res:
                    hasSentSignal = True
                    logger.info(f"Signal sent: { body}")
        time.sleep(TIME_SLEEP)


def _cal_change(close, pre_close):
    per = (close - pre_close) / pre_close * 100
    # if -0.9 <= per < 0.9:
    #     return ""
    per = per >= 0 and f"(+{per:.2f}%)" or f"({per:.2f}%)"
    return per


def cal_change(close, pre_close):
    per = (close - pre_close) / pre_close * 100
    per = per >= 0 and f"(+{per:.2f}%)" or f"({per:.2f}%)"
    return per


def pre_send_signal(timestamp, time_frame):
    """
    Check if 80% of the time frame has passed
    """
    if time_frame in TIME_FRAME_MS:
        ts = int(time.time())
        return ts >= timestamp + TIME_FRAME_MS[time_frame] * 0.9
    return False


def delete_message(body):
    URL = "http://localhost:8000/deleteMessage"
    headers = {"Content-Type": "application/json"}
    res = requests.post(URL, headers=headers, data=json.dumps(body), timeout=None)
    if res.json()["status"]:
        return True
    else:
        return False


def send_telegram_message(body):
    URL = "http://localhost:8000/sendMessage"
    headers = {"Content-Type": "application/json"}
    res = requests.post(URL, headers=headers, data=json.dumps(body), timeout=None)
    if res.json()["status"] == "success":
        return res.json()
    else:
        return False


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


def run_strategy(token, time_frame, pair, TIME_SLEEP, MODE, EXCHANGE):
    while True:
        try:
            print("STARTING CE BOT")
            data = init_data()
            main(data, token, time_frame, pair, TIME_SLEEP, MODE, EXCHANGE)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    # Set up argparse to handle command-line arguments
    parser = argparse.ArgumentParser(description="Process trading pair and timeframe.")
    parser.add_argument("--timeframe", type=str, help='Time frame, e.g., "1m"', default="1m")
    parser.add_argument("--sleep", type=str, help='Time sleep, e.g., "15"', default="10")
    parser.add_argument("--mode", type=str, help='Chart mode, e.g., "heikin_ashi/normal"', default="")
    parser.add_argument("--exchange", type=str, help='Exchange, e.g., "future/spot"', default="spot")

    args = parser.parse_args()

    MODE = args.mode
    TIME_FRAME = args.timeframe
    TIME_SLEEP = int(args.sleep)
    EXCHANGE = args.exchange

    # Each .txt file for each time frame
    files = {
        "1m": "tokens.1m.txt",
        "3m": "tokens.txt",
        "5m": "tokens.15m.normal.txt",
        "15m": "tokens.15m.txt",
        "15mnormal": "tokens.15m.normal.txt",
        "5mnormal": "tokens.15m.normal.txt",
        "30mnormal": "tokens.30m.txt",
        "30m": "tokens.30m.txt",
        "1h": "tokens.txt",
        "2h": "tokens.txt",
        "4h": "tokens.txt",
    }

    with open(files[f"{TIME_FRAME}{MODE}"], "r") as file:
        tokens = [line.strip() for line in file]

    strategies = [(token, TIME_FRAME, f"{token}USDT") for token in tokens]

    processes = []
    for token, time_frame, pair in strategies:
        process = multiprocessing.Process(
            target=run_strategy, args=(token, time_frame, pair, TIME_SLEEP, MODE, EXCHANGE)
        )
        processes.append(process)
        process.start()
