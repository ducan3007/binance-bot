import os

PIN_MESSAGE_PATH = "pinned_messages.txt"


def last_pinned_message_to_file(message_id, symbol, time_frame):
    records = {}

    # Read existing records from the file
    if os.path.exists(PIN_MESSAGE_PATH):
        with open(PIN_MESSAGE_PATH, "r") as file:
            for line in file:
                parts = line.strip().split()
                if len(parts) == 3:
                    existing_symbol, existing_message_id, existing_time_frame = parts
                    records[existing_symbol] = (existing_message_id, existing_time_frame)

    # Update or insert the new record
    records[symbol] = (message_id, time_frame)

    # Write the updated records back to the file
    with open(PIN_MESSAGE_PATH, "w") as file:
        for symbol, (message_id, time_frame) in records.items():
            file.write(f"{symbol} {message_id} {time_frame}\n")


# Example usage
last_pinned_message_to_file(12345, "AAPL", "1h")
last_pinned_message_to_file(67890, "GOOGL", "1d")
last_pinned_message_to_file(54321, "AAPL", "5m")
