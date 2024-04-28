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
current_timeframe = "5m"
print(f"Next candle start time for {current_timeframe}: {next_candle_start_time(current_timeframe)}")
