import requests
import time
from collections import defaultdict


TOKEN = "7489321215:AAF_i_0x-8pgEI-6wd71t917NRqs4bjHooc"
GROUP_CHAT_ID = "-1002194508247"

# Dictionary to hold aggregated messages
aggregated_messages = defaultdict(list)
# To hold the message IDs for deletion
message_ids = defaultdict(list)


def fetch_updates(offset=None):
    url = f"https://api.telegram.org/bot{TOKEN}/getUpdates"
    params = {}
    response = requests.get(url, params=params)
    return response.json()


def send_message(message):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": GROUP_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    response = requests.post(url, data=data)
    return response.json()  # Return response to get message ID


def delete_message(message_id):
    url = f"https://api.telegram.org/bot{TOKEN}/deleteMessage"
    data = {"chat_id": GROUP_CHAT_ID, "message_id": message_id}
    requests.post(url, data=data)


def process_messages(updates):
    for update in updates["result"]:
        message = update.get("message")
        if message and "text" in message:
            text = message["text"]
            message_id = message["message_id"]  # Get the message ID
            # Check if the message is a signal
            if "🟢" in text:
                # Extract time, token, and percentage from the message
                parts = text.split()
                if len(parts) >= 4:  # Ensure there are enough parts to process
                    time_part = parts[1]
                    token = parts[2]
                    percentage = " ".join(parts[3:])
                    # Append to the aggregated messages by time
                    aggregated_messages[time_part].append(f"{token} {percentage}")
                    # Keep track of the message ID for deletion
                    message_ids[time_part].append(message_id)


def aggregate_and_send():
    # Clear previously processed messages
    aggregated_messages.clear()
    message_ids.clear()

    updates = fetch_updates()
    process_messages(updates)

    for time_part, tokens in aggregated_messages.items():
        # Sort tokens alphabetically
        tokens.sort()
        # Create the aggregated message
        message = "\n".join([f"🟢 {time_part} {token}" for token in tokens])
        sent_message_response = send_message(message)
        if "result" in sent_message_response:
            sent_message_id = sent_message_response["result"]["message_id"]
            # Delete the original messages
            for msg_id in message_ids[time_part]:
                delete_message(msg_id)


if __name__ == "__main__":
    offset = None
    updates = fetch_updates(offset)
    for update in updates["result"]:
        print(update)
    # while True:
    #     aggregate_and_send()
    #     time.sleep(30)  # Run every 30 seconds
