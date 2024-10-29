import requests
from tabulate import tabulate
import json
import os

TOP_100_VOL = 100
TOP_OI = 40
TOP_VOL = 40

# Binance API endpoint for futures data
BASE_URL = "https://fapi.binance.com"

# File paths to save the data
VOL_FILE = "top_quote_vol.json"
OI_FILE = "top_open_interest.json"


# Function to format numbers into K, M, B
def format_number(num):
    num = float(num)
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.2f}B"
    elif num >= 1_000_000:
        return f"{num/1_000_000:.2f}M"
    elif num >= 1_000:
        return f"{num/1_000:.2f}K"
    else:
        return f"{num:.2f}"


# Function to get the 24hr ticker price change statistics (includes quoteVolume data and current price)
def get_futures_quote_volume(data):
    if not data:
        endpoint = "/fapi/v1/ticker/24hr"
        url = BASE_URL + endpoint
        response = requests.get(url)
        data = response.json()

    # Filter USDT pairs and sort by quoteVolume
    usdt_pairs = [item for item in data if item["symbol"].endswith("USDT")]
    sorted_usdt_pairs = sorted(usdt_pairs, key=lambda x: float(x["quoteVolume"]), reverse=True)

    # Top 100 USDT pairs by quoteVolume
    top_100_quote_vol = sorted_usdt_pairs[:TOP_100_VOL]
    return top_100_quote_vol


# Function to get the open interest for a specific pair
def get_open_interest(symbol):
    endpoint = f"/fapi/v1/openInterest"
    url = BASE_URL + endpoint
    params = {"symbol": symbol}
    response = requests.get(url, params=params)

    open_interest_data = response.json()
    return open_interest_data.get("openInterest")


# Function to get the top 50 USDT pairs by open interest (in USDT value) from top 100 quoteVolume pairs
def fetch_top_open_interest_usdt_from_top_100_quote_vol():
    # Fetch top 100 pairs by quoteVolume
    top_100_pairs = get_futures_quote_volume()

    oi_data = []
    filtered_top_100_pairs = []

    for pair in top_100_pairs:
        symbol = pair["symbol"]
        oi_value = get_open_interest(symbol)
        price = float(pair["lastPrice"])  # Use the last price from the 24hr stats

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

    # Sort by open interest USDT value and take the top 50
    sorted_oi_data = sorted(
        oi_data,
        key=lambda x: float(
            x["openInterestUSDT"].replace(",", "").replace("K", "e3").replace("M", "e6").replace("B", "e9")
        ),
        reverse=True,
    )
    return sorted_oi_data[:TOP_OI], filtered_top_100_pairs[:TOP_VOL]


# Function to load previous data from a file
def load_previous_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    return None  # Return None if the file does not exist


# Function to save the current data into a file
def save_current_data(data, file_path):
    with open(file_path, "w") as file:
        json.dump(data, file, indent=4)


# Function to check for new tokens and return a display version with '*' if necessary
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


# Fetch and print the data in two tables
if __name__ == "__main__":
    # Load previous data
    previous_vol_data = load_previous_data(VOL_FILE)
    previous_oi_data = load_previous_data(OI_FILE)

    # Fetch top 50 by open interest USDT value from the top 100 quoteVolume pairs
    top_oi_usdt, top_quote_vol = fetch_top_open_interest_usdt_from_top_100_quote_vol()

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


    # Create a combined table with Volume and Open Interest tokens
    combined_table = []
    for i in range(max(len(display_quote_vol), len(display_oi_usdt))):
        vol_token = display_quote_vol[i]["token"] if i < len(display_quote_vol) else ""
        vol_value = display_quote_vol[i]["quoteVolume"] if i < len(display_quote_vol) else ""
        oi_token = display_oi_usdt[i]["token"] if i < len(display_oi_usdt) else ""
        oi_value = display_oi_usdt[i]["openInterestUSDT"] if i < len(display_oi_usdt) else ""
        combined_table.append((vol_token, vol_value, oi_token, oi_value))

    # Print the combined table
    print(tabulate(combined_table, tablefmt="plain"))
