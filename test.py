import os

PIN_MESSAGE_PATH = 'pinned_messages.txt'

def last_pinned_message_to_file(message_id, symbol, time_frame):
    records = []

    # Read existing records from the file
    if os.path.exists(PIN_MESSAGE_PATH):
        with open(PIN_MESSAGE_PATH, "r") as file:
            for line in file:
                parts = line.strip().split()
                if len(parts) == 3:
                    existing_symbol, existing_message_id, existing_time_frame = parts
                    records.append((existing_symbol, existing_message_id, existing_time_frame))

    # Update or insert the new record
    record_updated = False
    for i, (existing_symbol, existing_message_id, existing_time_frame) in enumerate(records):
        if existing_symbol == symbol and existing_time_frame == time_frame:
            records[i] = (symbol, message_id, time_frame)
            record_updated = True
            break
    
    if not record_updated:
        records.append((symbol, message_id, time_frame))

    # Write the updated records back to the file
    with open(PIN_MESSAGE_PATH, "w") as file:
        for symbol, message_id, time_frame in records:
            file.write(f"{symbol} {message_id} {time_frame}\n")

# Example usage
last_pinned_message_to_file(12111115, 'AAPL', '15m')
last_pinned_message_to_file(67890, 'GOOGL', '1d')
last_pinned_message_to_file(54321111, 'AAPL', '1h')  # This will replace the old record with symbol 'AAPL' and time_frame '1h'
