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

_append_data(data1, data2)
print(data1)
