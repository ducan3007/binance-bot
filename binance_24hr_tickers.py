import os
import json
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
                f"+{gainer['priceChangePercent']:.1f}%" if gainer["priceChangePercent"] != "" else "",
                f"{loser['priceChangePercent']:.1f}%" if loser["priceChangePercent"] != "" else "",
                loser["symbol"],
            ]
        )

    return tabulate(table_data, tablefmt="plain", colalign=("left", "right", "left", "left"))


def load_previous_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    return None


def save_current_data(data, file_path):
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)


def check_new_tokens_display(current_data, previous_data):
    if previous_data is None:
        # No previous data, so return the tokens as-is without marking them
        return current_data

    previous_tokens = {item["token"] for item in previous_data}
    display_data = []
    for item in current_data:
        # Append '*' to new tokens for display purposes only
        token_display = item["token"] + "*" if item["token"] not in previous_tokens else item["token"]
        display_data.append({**item, "token": token_display})
    return display_data


def format_oi_vol_table(data):
    previous_oi_data = load_previous_data(OI_FILE)
    previous_vol_data = load_previous_data(VOL_FILE)

    top_oi_usdt = data["top_oi_usdt"]
    top_quote_vol = data["top_quote_vol"]

    # Prepare display data with '*' for new tokens (without affecting data saved in files)
    display_oi_usdt = check_new_tokens_display(top_oi_usdt, previous_oi_data)
    display_quote_vol = check_new_tokens_display(
        [
            {"token": item["symbol"].replace("USDT", ""), "quoteVolume": format_number(item["quoteVolume"])}
            for item in top_quote_vol
        ],
        previous_vol_data,
    )

    # Save the original current data (without '*' for new tokens) into files
    save_current_data(top_oi_usdt, OI_FILE)
    save_current_data(
        [
            {"token": item["symbol"].replace("USDT", ""), "quoteVolume": format_number(item["quoteVolume"])}
            for item in top_quote_vol
        ],
        VOL_FILE,
    )

    # Create a combined table with Volume and Open Interest tokens, formatted as: TOKEN VOL OI TOKEN
    combined_table = []
    for i in range(max(len(display_quote_vol), len(display_oi_usdt))):
        vol_token = display_quote_vol[i]["token"] if i < len(display_quote_vol) else ""
        vol_value = display_quote_vol[i]["quoteVolume"] if i < len(display_quote_vol) else ""
        oi_value = display_oi_usdt[i]["openInterestUSDT"] if i < len(display_oi_usdt) else ""
        oi_token = display_oi_usdt[i]["token"] if i < len(display_oi_usdt) else ""
        # Append the values in the new format: TOKEN VOL OI TOKEN
        combined_table.append((vol_token, vol_value, oi_value, oi_token))

    colalign = ("left", "right", "left", "left") 
    return tabulate(combined_table, tablefmt="plain", colalign=colalign)


def get_24h_price_change():
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    response = requests.get(url)
    data = response.json()
    return data


# Function to get the open interest for a specific pair
def get_open_interest(symbol, OPEN_INTEREST_MAP):
    endpoint = f"https://fapi.binance.com/fapi/v1/openInterest"
    params = {"symbol": symbol}
    response = requests.get(endpoint, params=params)

    open_interest_data = response.json()
    oi_value = open_interest_data.get("openInterest")

    if oi_value:
        OPEN_INTEREST_MAP[symbol] = oi_value

    return oi_value


def filter_usdt_pairs(data):
    usdt_pairs = [ticker for ticker in data if ticker["symbol"].endswith("USDT")]
    return usdt_pairs


def format_number(num):
    num = float(num)
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{round(num/1_000_000)}M"
    elif num >= 1_000:
        return f"{round(num/1_000)}K"
    else:
        return f"{num:.1f}"


def get_top_gainers_and_losers(data, OPEN_INTEREST_MAP):
    print("Getting top gainers and losers")
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
            oi_value = get_open_interest(candidate["symbol"], OPEN_INTEREST_MAP)
            if oi_value:
                OPEN_INTEREST_MAP[candidate["symbol"]] = oi_value
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
            oi_value = get_open_interest(candidate["symbol"], OPEN_INTEREST_MAP)
            if oi_value:
                OPEN_INTEREST_MAP[candidate["symbol"]] = oi_value
                counter += 1
                if float(candidate["priceChangePercent"]) > -1.0:
                    break
                top_losers.append(candidate)
        losers_idx += 1

    logger.info(f"Total pairs checked: {counter}")
    return top_gainers, top_losers


TOP_100_VOL = 100
TOP_OI = 40
TOP_VOL = 40

VOL_FILE = "top_quote_vol.json"
OI_FILE = "top_open_interest.json"


def fetch_top_open_interest_usdt_from_top_100_quote_vol(usdt_pairs, OPEN_INTEREST_MAP):
    print("Fetching top open interest USDT from top 100 quote volume")
    oi_data = []
    filtered_top_100_pairs = []
    sorted_usdt_pairs = sorted(usdt_pairs, key=lambda x: float(x["quoteVolume"]), reverse=True)
    top_100_pairs = sorted_usdt_pairs[:TOP_100_VOL]

    for pair in top_100_pairs:
        symbol = pair["symbol"]
        price = float(pair["lastPrice"])  # Use the last price from the 24hr stats
        oi_value = get_open_interest(symbol, OPEN_INTEREST_MAP)

        if oi_value:
            oi_usdt_value = float(oi_value) * price  # Calculate Open Interest in USDT
            oi_data.append(
                {
                    "token": symbol.replace("USDT", ""),  # Remove 'USDT' from the symbol
                    "quoteVolume": format_number(pair["quoteVolume"]),
                    "openInterestUSDT": format_number(oi_usdt_value),
                }
            )
            # Add to filtered list if OI exists
            filtered_top_100_pairs.append(pair)
        else:
            print(f"Warning: No openInterest data for {symbol}")

    sorted_oi_data = sorted(
        oi_data,
        key=lambda x: float(
            x["openInterestUSDT"].replace(",", "").replace("K", "e3").replace("M", "e6").replace("B", "e9")
        ),
        reverse=True,
    )
    return sorted_oi_data[:TOP_OI], filtered_top_100_pairs[:TOP_VOL]


def main(OPEN_INTEREST_MAP):
    start = time.time()
    data = get_24h_price_change()
    usdt_pairs = filter_usdt_pairs(data)

    top_gainers, top_losers = get_top_gainers_and_losers(usdt_pairs, OPEN_INTEREST_MAP)
    top_oi_usdt, top_quote_vol = fetch_top_open_interest_usdt_from_top_100_quote_vol(usdt_pairs, OPEN_INTEREST_MAP)

    result = {
        "gainers": [
            {"symbol": ticker["symbol"].replace("USDT", ""), "priceChangePercent": float(ticker["priceChangePercent"])}
            for ticker in top_gainers
        ],
        "losers": [
            {"symbol": ticker["symbol"].replace("USDT", ""), "priceChangePercent": float(ticker["priceChangePercent"])}
            for ticker in top_losers
        ],
        "top_oi_usdt": top_oi_usdt,
        "top_quote_vol": top_quote_vol,
    }

    logger.info(f"Time taken: {time.time() - start:.2f} seconds")
    return result


def binance_24hr_tickers():
    OPEN_INTEREST_MAP = {}
    message = main(OPEN_INTEREST_MAP)

    table_vol_oi = format_oi_vol_table(message)
    table = format_table(message)

    print("Top 50 Gainers & Losers 24hr\n", table)
    print("\nTop 40 Volume Trade and Open Interest \n", table_vol_oi)

    """
    Display
    """

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

    print("gain", gainers_idx)
    print("losers", losers_idx)
    message = f"#DAILY_REPORT {date} {trend}\n\nBinance Future\n\nTop 50 Gainers & Losers 24hr {trend1}\n\n<pre language='javascript'>{table}</pre>\n\nTop Volume Trade and Open Interest\n\n<pre language='javascript'>{table_vol_oi}</pre>"
    URL = "http://localhost:8000/send24hrPriceChange"
    response = requests.post(
        URL,
        json={"message": message, "time_frame": "4h"},
        headers={"Content-Type": "application/json"},
    )
    print(response.json())
