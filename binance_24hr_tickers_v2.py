import requests
import time
from tabulate import tabulate
from logger import logger

N = 50


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


def get_24h_price_change():
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    response = requests.get(url)
    data = response.json()
    return data


def check_symbol_trade_status(symbol):
    url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
    response = requests.get(url)
    if response.status_code == 200:
        return True
    return False


def filter_usdt_pairs(data):
    usdt_pairs = [ticker for ticker in data if ticker["symbol"].endswith("USDT")]
    return usdt_pairs


def get_top_gainers_and_losers(data):
    sorted_data = sorted(data, key=lambda x: float(x["priceChangePercent"]), reverse=True)

    top_gainers = []
    top_losers = []

    gainers_checked = set()
    losers_checked = set()

    gainers_idx = 0
    losers_idx = 0
    counter = 0
    # Collect top gainers
    while len(top_gainers) < N and gainers_idx < len(sorted_data):
        candidate = sorted_data[gainers_idx]
        if candidate["symbol"] not in gainers_checked:
            gainers_checked.add(candidate["symbol"])
            if check_symbol_trade_status(candidate["symbol"]):
                counter += 1
                if float(candidate["priceChangePercent"]) < 1.0:
                    break
                top_gainers.append(candidate)
        gainers_idx += 1

    # Collect top losers
    sorted_losers_data = sorted(data, key=lambda x: float(x["priceChangePercent"]))
    while len(top_losers) < N and losers_idx < len(sorted_losers_data):
        candidate = sorted_losers_data[losers_idx]
        if candidate["symbol"] not in losers_checked:
            losers_checked.add(candidate["symbol"])
            if check_symbol_trade_status(candidate["symbol"]):
                counter += 1
                if float(candidate["priceChangePercent"]) > -1.0:
                    break
                top_losers.append(candidate)
        losers_idx += 1

    logger.info(f"Total pairs checked: {counter}")
    return top_gainers, top_losers


def main():
    start = time.time()
    data = get_24h_price_change()
    usdt_pairs = filter_usdt_pairs(data)
    top_gainers, top_losers = get_top_gainers_and_losers(usdt_pairs)

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
    date = time.strftime("%Y-%m-%d", time.localtime())
    message = (
        f"#DAILY_REPORT {date}\n\nBinance Future Top 50 Gainers & Losers 📊\n\n<pre language='javascript'>{table}</pre>"
    )
    URL = "http://localhost:8000/send24hrPriceChange"
    response = requests.post(
        URL,
        json={"message": message, "time_frame": "2h"},
        headers={"Content-Type": "application/json"},
    )
    print(response.json())
