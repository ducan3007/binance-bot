import yfinance as yf

def get_latest_gold_futures_price():
    """
    Fetch the latest gold futures price using yfinance.

    Returns:
    - float: Latest gold futures price in USD.
    """
    try:
        # Gold futures ticker symbol on Yahoo Finance
        gold_futures_ticker = "GC=F"
        
        # Create a Ticker object
        gold_futures = yf.Ticker(gold_futures_ticker)
        
        # Fetch the latest market data
        gold_futures_data = gold_futures.history(period="1d")
        
        # Extract the latest closing price
        latest_price = gold_futures_data['Close'].iloc[-1]
        
        return latest_price
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Example usage
if __name__ == "__main__":
    price = get_latest_gold_futures_price()
    if price is not None:
        print(f"Latest Gold Futures Price: ${price:.2f} per ounce")
    else:
        print("Failed to retrieve the latest gold futures price.")
