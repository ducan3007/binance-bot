import requests
import time
from tabulate import tabulate
from logger import logger


def format_table(data):
    gainers = data["gainers"]
    losers = data["losers"]
    max_len = max(len(gainers), len(losers))
    if len(gainers) < max_len:
        gainers.extend([{"symbol": "", "priceChangePercent": ""}] * (max_len - len(gainers)))
    if len(losers) < max_len:
        losers.extend([{"symbol": "", "priceChangePercent": ""}] * (max_len - len(losers)))

    table_data = []
    for gainer, loser in zip(gainers, losers):
        table_data.append(
            [
                gainer["symbol"],
                f"+{gainer['priceChangePercent']:.2f}%" if gainer["priceChangePercent"] != "" else "",
                loser["symbol"],
                f"{loser['priceChangePercent']:.2f}%" if loser["priceChangePercent"] != "" else "",
            ]
        )

    return tabulate(table_data, headers=["GAINERS", "24h%", "LOSERS", "24h%"], tablefmt="simple")


def get_24h_price_change(symbol):
    url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}"
    response = requests.get(url)
    data = response.json()
    return data


def get_top_gainers_and_losers(tokens):
    data = []
    for symbol in tokens:
        try:
            ticker_data = get_24h_price_change(symbol)
            data.append(ticker_data)
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {e}")

    print(data)
    sorted_data = sorted(data, key=lambda x: float(x["priceChangePercent"]), reverse=True)

    top_gainers = [item for item in sorted_data if float(item["priceChangePercent"]) > 0][:50]

    sorted_data = sorted(data, key=lambda x: float(x["priceChangePercent"]), reverse=False)
    top_losers = [item for item in sorted_data if float(item["priceChangePercent"]) < 0][-50:]

    return top_gainers, top_losers


def main():
    start = time.time()

    with open(f"tokens.15m.normal.txt", "r") as file:
        tokens = [f"{line.strip()}USDT" for line in file]

    top_gainers, top_losers = get_top_gainers_and_losers(tokens)

    result = {
        "gainers": [
            {"symbol": ticker["symbol"].replace("USDT", ""), "priceChangePercent": float(ticker["priceChangePercent"])}
            for ticker in top_gainers
        ],
        "losers": [
            {"symbol": ticker["symbol"].replace("USDT", ""), "priceChangePercent": float(ticker["priceChangePercent"])}
            for ticker in top_losers
        ],
    }

    logger.info(f"Time taken: {time.time() - start:.2f} seconds")
    return result


if __name__ == "__main__":
    message = main()
    table = format_table(message)
    date = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))
    down = "🔻🔻🔻"
    up = "🟢🟢🟢"

    down1 = "📉"
    up1 = "📈"
    losers_idx, gainers_idx = 0, 0

    for gainer in message["gainers"]:
        if gainer["priceChangePercent"] and float(gainer["priceChangePercent"]) > 0:
            gainers_idx += 1

    for loser in message["losers"]:
        if loser["priceChangePercent"] and float(loser["priceChangePercent"]) < 0:
            losers_idx += 1

    if gainers_idx > losers_idx:
        trend = up
        trend1 = up1
    elif gainers_idx < losers_idx:
        trend = down
        trend1 = down1
    else:
        if float(message["gainers"][0]["priceChangePercent"]) > float(message["losers"][0]["priceChangePercent"]):
            trend = up
            trend1 = up1
        else:
            trend = down
            trend1 = down1

    message = f"#DAILY_REPORT {date} {trend}\n\nBinance Future\nTop Gainers & Losers {trend1}\n\n<pre language='javascript'>{table}</pre>"
    URL = "http://localhost:8000/send24hrPriceChange"
    response = requests.post(
        URL,
        json={"message": message, "time_frame": "15m_normal"},
        headers={"Content-Type": "application/json"},
    )
    print(response.json())
