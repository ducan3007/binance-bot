from datetime import datetime, timedelta


def next_candle_start_time(timeframe):
    # Define timeframes in minutes
    timeframes = {
        "5m": 5,
        "15m": 15,
        # Add more timeframes if necessary
    }

    # Get the current time
    now = datetime.now()

    # Get the interval in minutes from the timeframe
    interval = timeframes.get(timeframe)
    if not interval:
        raise ValueError("Invalid timeframe provided.")

    # Calculate the number of minutes past since the last interval
    minutes_past = now.minute % interval

    # Calculate how many minutes to the next candle
    minutes_to_next = interval - minutes_past

    # Calculate the start time of the next candle
    next_candle_time = now + timedelta(minutes=minutes_to_next)

    # Reset seconds and microseconds to zero to align with candle start
    next_candle_time = next_candle_time.replace(second=0, microsecond=0)

    # Convert to Unix timestamp in milliseconds
    next_candle_timestamp = int(next_candle_time.timestamp())

    return next_candle_timestamp


# Example usage


def _append_data(data1, data2):
    # Append data from data2 to data1
    for key in data1:
        data1[key].extend(data2[key])


data1 = {
    "Open": [1, 2, 3],
    "High": [4, 5, 6],
    "Low": [7, 8, 9],
    "Close": [10, 11, 12],
    "Time": [13, 14, 15],
    "ATR": [16, 17, 18],
    "LongStop": [19, 20, 21],
    "ShortStop": [22, 23, 24],
    "LongStopPrev": [25, 26, 27],
    "ShortStopPrev": [28, 29, 30],
    "Direction": [31, 32, 33],
}

data2 = {
    # only have 2 itmes in array
    "Open": [1, 2],
    "High": [4, 5],
    "Low": [7, 8],
    "Close": [10, 11],
    "Time": [13, 14],
    "ATR": [16, 17],
    "LongStop": [19, 20],
    "ShortStop": [22, 23],
    "LongStopPrev": [25, 26],
    "ShortStopPrev": [28, 29],
    "Direction": [31, 32],
}


class Message:
    def __init__(self, symbol, signal, price):
        self.symbol = symbol
        self.signal = signal
        self.price = price


# Mock-up dictionary for signal icons
Signals = {"buy": "🔴", "sell": "🟢"}


def construct_message(message: Message):
    # Define the desired length for alignment
    max_length = 6  # Adjust this value based on your maximum expected token length
    # Align the symbol and format the message
    aligned_symbol = message.symbol.ljust(max_length)
    return f"{aligned_symbol} {Signals[message.signal]}\n\nPrice: {message.price}"


# Example usage
message1 = Message("TAO", "buy", 100)
message2 = Message("W", "sell", 200)
message3 = Message("TOKEN", "buy", 300)

print(construct_message(message1))
print(construct_message(message2))
print(construct_message(message3))


float = 0.0084697
print(f"{float:.8f}")
print(float)
print(0.00002702)