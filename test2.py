import os

PIN_MESSAGE_PATH = "pinned_messages.txt"


def get_message_id(symbol, time_frame):
    # Check if the file exists
    if not os.path.exists(PIN_MESSAGE_PATH):
        return None

    # Read the records from the file
    with open(PIN_MESSAGE_PATH, "r") as file:
        for line in file:
            parts = line.strip().split()
            if len(parts) == 3:
                existing_symbol, existing_message_id, existing_time_frame = parts
                if existing_symbol == symbol and existing_time_frame == time_frame:
                    return existing_message_id
    return None


symbol = "AAPL"
time_frame = "1h"
message_id = get_message_id(symbol, time_frame)
if message_id:
    print(f"Message ID: {message_id}")
else:
    print("Message ID not found")
