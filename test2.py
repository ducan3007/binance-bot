import pandas as pd

# Path to your CSV file
csv_path = "BTC_ce.csv"

# Load the data from CSV
data = pd.read_csv(csv_path)


# Initialize parameters
initial_capital = 1000
current_capital = initial_capital
leverage = 5
fee_rate = 0.0025
position_open = False
position_type = None  # 'long' or 'short'
open_price = 0

# Iterate over the rows of the dataset to apply the trading strategy
for index, row in data.iterrows():
    if index == 0:
        continue  # Skip the first row as there's no previous data to compare with

    previous_row = data.iloc[index - 1]

    # Check for direction change and open/close positions
    if previous_row["direction"] == -1 and row["direction"] == 1:
        # Close short and open long position
        if position_open and position_type == "short":
            # Calculate profit from the short position
            profit = (previous_row["real_price_open"] - row["real_price_close"]) / previous_row["real_price_open"]
            current_capital += current_capital * profit * leverage
            current_capital -= current_capital * fee_rate  # Apply transaction fee

        # Open new long position
        position_type = "long"
        open_price = row["real_price_open"]

    elif previous_row["direction"] == 1 and row["direction"] == -1:
        # Close long and open short position
        if position_open and position_type == "long":
            # Calculate profit from the long position
            profit = (row["real_price_close"] - open_price) / open_price
            current_capital += current_capital * profit * leverage
            current_capital -= current_capital * fee_rate  # Apply transaction fee

        # Open new short position
        position_type = "short"
        open_price = row["real_price_open"]

    position_open = True

# Calculate final results
final_capital = current_capital
percentage_gain = ((final_capital - initial_capital) / initial_capital) * 100

# Output results
print(f"Initial Capital: ${initial_capital}")
print(f"Final Capital: ${final_capital:.2f}")
print(f"Percentage Gain: {percentage_gain:.2f}%")
