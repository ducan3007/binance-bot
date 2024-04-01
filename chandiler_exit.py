from datetime import datetime
import sys
import os
import math
import numpy as np
import pandas as pd
import datetime
from finta import TA
from binance.spot import Spot
from datetime import datetime, timezone, timedelta


client = Spot()


def load_historic_data(symbol):
    try:
        data = []
        klines = client.klines("SOLUSDT", "15m", limit=10)
        for kline in klines:
            data.append(
                [
                    float(kline[1]),  # Open
                    float(kline[2]),  # High
                    float(kline[3]),  # Low
                    float(kline[4]),  # Close
                ]
            )
        df = pd.DataFrame(data, columns=["Open", "High", "Low", "Close"])
        return df
    except:
        print("Error loading stock data for " + symbol)
        return None


def calculate_tis(df, atr_period, atr_multiplier):
    atr = TA.ATR(df, period=atr_period)
    chandelier_info = TA.CHANDELIER(
        df, short_period=atr_period, long_period=atr_period, k=3
    )
    df = pd.concat([df, atr, chandelier_info], axis=1, ignore_index=False)

    return df


def calculate_signals(df):
    #  Long position
    df["enter_long"] = np.where(
        (df["close"] > df["Short."]) & (df["close"].shift(1) <= df["Short."].shift(1)),
        1,
        0,
    )
    df["exit_long"] = np.where(
        (df["close"] < df["Long."]) & (df["close"].shift(1) >= df["Long."].shift(1)),
        1,
        0,
    )

    #  Short position
    df["enter_short"] = np.where(
        (df["close"] < df["Long."]) & (df["close"].shift(1) >= df["Long."].shift(1)),
        1,
        0,
    )
    df["exit_short"] = np.where(
        (df["close"] > df["Short."]) & (df["close"].shift(1) <= df["Short."].shift(1)),
        1,
        0,
    )
    return df


def execute_strategy(df):
    close_prices = df["close"].to_numpy()
    enter_long = df["enter_long"].to_numpy()
    exit_long = df["exit_long"].to_numpy()
    enter_short = df["enter_short"].to_numpy()
    exit_short = df["exit_short"].to_numpy()

    last_long_entry_price = 0
    last_short_entry_price = 0
    long_entry_prices = []
    long_exit_prices = []
    short_entry_prices = []
    short_exit_prices = []
    hold_long = 0
    hold_short = 0

    for i in range(len(close_prices)):
        current_price = close_prices[i]

        #  Enter long
        if hold_long == 0 and enter_long[i] == 1:
            last_long_entry_price = current_price
            long_entry_prices.append(current_price)
            long_exit_prices.append(np.nan)
            hold_long = 1
        #  Exit long
        elif hold_long == 1 and exit_long[i] == 1:
            long_entry_prices.append(np.nan)
            long_exit_prices.append(current_price)
            hold_long = 0
        else:
            #  Neither entry nor exit
            long_entry_prices.append(np.nan)
            long_exit_prices.append(np.nan)

        #  Enter Short
        if hold_short == 0 and enter_short[i] == 1:
            last_short_entry_price = current_price
            short_entry_prices.append(current_price)
            short_exit_prices.append(np.nan)
            hold_short = 1
        #  Exit short
        elif hold_short == 1 and exit_short[i] == 1:
            short_entry_prices.append(np.nan)
            short_exit_prices.append(current_price)
            hold_short = 0
        else:
            #  Neither entry nor exit
            short_entry_prices.append(np.nan)
            short_exit_prices.append(np.nan)

    return long_entry_prices, long_exit_prices, short_entry_prices, short_exit_prices
