import pandas as pd
from binance.spot import Spot as Client
from datetime import datetime
import pytz

# Initialize Binance Spot client
client = Client()

def fetch_candles(symbol, interval, limit=1500):
    candles = client.klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(candles, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    return df

def calculate_chandelier_exit(df, atr_period=1, atr_multiplier=2):
    # Calculate True Range
    df['tr'] = df[['high', 'low', 'close']].apply(lambda x: max(x['high'] - x['low'], abs(x['high'] - x['close']), abs(x['low'] - x['close'])), axis=1)
    # Calculate ATR
    df['atr'] = df['tr'].rolling(window=atr_period).mean()
    # Calculate Chandelier Exit Long and Short
    df['long_stop'] = df['high'].rolling(window=atr_period).max() - df['atr'] * atr_multiplier
    df['short_stop'] = df['low'].rolling(window=atr_period).min() + df['atr'] * atr_multiplier
    return df

symbol = 'SOLUSDT'
interval = '15m'
df = fetch_candles(symbol, interval)
df_ce = calculate_chandelier_exit(df)

# Convert timestamp to UTC+7
df_ce['timestamp'] = df_ce['timestamp'].dt.tz_localize('UTC').dt.tz_convert('Asia/Bangkok')

# Identify 'Long Stop Start' and 'Short Stop Start'
df_ce['long_stop_start'] = df_ce['close'] > df_ce['long_stop']
df_ce['short_stop_start'] = df_ce['close'] < df_ce['short_stop']

long_stop_starts = df_ce[df_ce['long_stop_start']]
short_stop_starts = df_ce[df_ce['short_stop_start']]

print("Long Stop Starts:")
print(long_stop_starts[['timestamp', 'close']])

print("\nShort Stop Starts:")
print(short_stop_starts[['timestamp', 'close']])
