from binance.spot import Spot
from datetime import datetime, timezone, timedelta


client = Spot()

# Get klines of BTCUSDT at 1m interval
# Get last 10 klines of BNBUSDT at 1h interval
sol_usdt_klines = client.klines("SOLUSDT", "15m", limit=10)

data = []


def parse_klines(klines):
    for kline in klines:
        data.append(
            [
                float(kline[1]),  # Open
                float(kline[2]),  # High
                float(kline[3]),  # Low
                float(kline[4]),  # Close
            ]
        )

    return data


print(parse_klines(sol_usdt_klines))
