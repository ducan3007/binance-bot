import pandas as pd
from datetime import datetime

leverage = 2
fee_rate = 0.004
position_fraction = 1.00
stop_lost = -0.05
tp = 0.05


time_frame = "15m"

time_frame_30m = False
time_frame_15m = True
enable_log = True


def check_time(time1):
    time_object = datetime.strptime(time1, "%Y-%m-%d %H:%M")
    current_time = time_object.time()
    start_time = datetime.strptime("01:15", "%H:%M").time()
    end_time = datetime.strptime("06:00", "%H:%M").time()
    if start_time <= current_time <= end_time:
        return False
    return True

def check_direction_15m_with_15m_ha(df_15m_ha, time_15m, pre_direction, direction_15m):
    if df_15m_ha is None:
        return True

    # Find the previous, current, and next 15m_ha candle rows
    pre_15m_ha_candle = df_15m_ha[df_15m_ha["Time"] == (time_15m - 900)]  # 900 seconds = 15 minutes
    current_15m_ha_candle = df_15m_ha[df_15m_ha["Time"] == time_15m]
    next_15m_ha_candle = df_15m_ha[df_15m_ha["Time"] == (time_15m + 900)]  # 900 seconds = 15 minutes

    # Check if the direction matches
    if not pre_15m_ha_candle.empty and not current_15m_ha_candle.empty:
        if pre_15m_ha_candle.iloc[0]["direction"] == pre_direction and current_15m_ha_candle.iloc[0]["direction"] == direction_15m:
            print("Check Previous 15m_ha and Current 15m_ha direction match", pre_15m_ha_candle.iloc[0]["Time1"], current_15m_ha_candle.iloc[0]["Time1"])
            return True
    
    if not current_15m_ha_candle.empty and not next_15m_ha_candle.empty:
        if current_15m_ha_candle.iloc[0]["direction"] == pre_direction and next_15m_ha_candle.iloc[0]["direction"] == direction_15m:
            print("Check Current 15m_ha and Next 15m_ha direction match", current_15m_ha_candle.iloc[0]["Time1"], next_15m_ha_candle.iloc[0]["Time1"])
            return True

    return False


# def check_direction_15m_with_15m_ha(df_15m_ha, time_15m, pre_direction, direction_15m):
#     if df_15m_ha is None:
#         return True

#     # Find the current and next 15m_ha candle rows
#     pre_15m_ha_candle = df_15m_ha[df_15m_ha["Time"] == (time_15m - 900)]  # 900 seconds = 15 minutes
#     current_15m_ha_candle = df_15m_ha[df_15m_ha["Time"] == time_15m]
#     next_15m_ha_candle = df_15m_ha[df_15m_ha["Time"] == (time_15m + 900)]  # 900 seconds = 15 minutes

#     # Check if the direction matches
#     if not current_15m_ha_candle.empty and direction_15m == current_15m_ha_candle.iloc[0]["direction"]:
#         print("Check Current 15m_ha direction matches", current_15m_ha_candle.iloc[0]["Time1"])
#         return True
#     elif not next_15m_ha_candle.empty and direction_15m == next_15m_ha_candle.iloc[0]["direction"]:
#         print("Check Next 15m_ha direction matches", next_15m_ha_candle.iloc[0]["Time1"])
#         return True
#     else:
#         return False


# def check_direction_15m_with_30m(df_30m, time_15m, pre_direction, direction_15m):
#     # return True
#     if df_30m is None:
#         return True
#     # Calculate the start time of the corresponding 30m interval
#     time_30m = time_15m // 1800 * 1800  # Floor division to find the start of the 30m interval

#     # Find the current and next 30m candle rows
#     current_30m_candle = df_30m[df_30m["Time"] == time_30m]
#     next_30m_candle = df_30m[df_30m["Time"] == (time_30m + 1800)]

#     # Check if the direction matches
#     if not current_30m_candle.empty and direction_15m == current_30m_candle.iloc[0]["direction"]:
#         print("Check Current 30m direction matches", current_30m_candle.iloc[0]["Time1"])
#         return True
#     # elif not next_30m_candle.empty and direction_15m == next_30m_candle.iloc[0]["direction"]:
#     #     # print("Check Next 30m direction matches", next_30m_candle.iloc[0]["Time1"])
#     #     return True
#     else:
#         return False

def check_direction_15m_with_30m(df_30m, time_15m, pre_direction, direction_15m):
    if df_30m is None:
        return True

    # Calculate the start time of the corresponding 30m interval
    time_30m = time_15m // 1800 * 1800  # Floor division to find the start of the 30m interval

    # Find the previous, current, and next 30m candle rows
    pre_30m_candle = df_30m[df_30m["Time"] == (time_30m - 1800)]
    current_30m_candle = df_30m[df_30m["Time"] == time_30m]
    next_30m_candle = df_30m[df_30m["Time"] == (time_30m + 1800)]

    # Check if the direction matches
    if not pre_30m_candle.empty and not current_30m_candle.empty:
        if pre_30m_candle.iloc[0]["direction"] == pre_direction and current_30m_candle.iloc[0]["direction"] == direction_15m:
            print("Check Previous 30m and Current 30m direction match", pre_30m_candle.iloc[0]["Time1"], current_30m_candle.iloc[0]["Time1"])
            return True

    if not current_30m_candle.empty and not next_30m_candle.empty:
        if current_30m_candle.iloc[0]["direction"] == pre_direction and next_30m_candle.iloc[0]["direction"] == direction_15m:
            print("Check Current 30m and Next 30m direction match", current_30m_candle.iloc[0]["Time1"], next_30m_candle.iloc[0]["Time1"])
            return True

    return False


def run_trading_strategy(token, time_frame):
    data = pd.read_csv(f"{token}_ce_{time_frame}.csv")

    if time_frame_15m:
        df_15m_ha = pd.read_csv(f"{token}_ce_15m_ha.csv")
    else:
        df_15m_ha = None

    if time_frame_30m:
        df_30m = pd.read_csv(f"{token}_ce_30m.csv")
    else:
        df_30m = None

    if df_30m is not None:
        df_data = df_30m
    else:
        df_data = df_15m_ha

    initial_capital = 2300
    capital = initial_capital
    position_open = False
    position_type = None
    entry_price = 0
    win = 0
    loss = 0
    max_loss = 0
    max_win = 0
    lowest_capital = capital
    current_loss_streak = 0
    max_loss_streak = 0
    long_opened = 0
    short_opened = 0
    daily_results = {}
    """
    {
    "2024-06-26": {"win": 5, "lost": 4},
    }
    """
    daily_win_lost = {}
    stop_lost_rate = 0

    highest_gain_open = 0  # To track highest gain while position is open
    gain_1_2_percent = 0
    gain_2_4_percent = 0
    gain_more_than_4_percent = 0

    print(f"Processing token: {token}")

    for i in range(2, len(data)):
        item = data.iloc[i]
        current_direction = item["direction"]
        current_close = item["real_price_close"]
        current_high = item["High"]
        current_low = item["Low"]

        previous_item = data.iloc[i - 1]
        previous_direction = previous_item["direction"]
        previous_close = previous_item["real_price_close"]

        pre_previous_item = data.iloc[i - 2]
        pre_previous_direction = pre_previous_item["direction"]

        current_date = item["Time1"][:10]
        if current_date not in daily_results:
            daily_results[current_date] = {"capital_start": capital, "gain_loss": 0}

        # Update highest gain while position is open
        if position_open:
            if position_type == "long":
                current_gain = (current_high - entry_price) / entry_price * leverage
            elif position_type == "short":
                current_gain = (entry_price - current_low) / entry_price * leverage
            if current_gain > highest_gain_open:
                highest_gain_open = current_gain

        # Close long position
        if position_open and position_type == "long":
            exit_price = previous_close
            gain_per = (exit_price - entry_price) / entry_price * leverage

            if gain_per <= stop_lost or gain_per >= tp:
                if gain_per >= tp:
                    gain_per = tp
                else:
                    gain_per = stop_lost
                    stop_lost_rate += 1

                gain = gain_per * (capital * position_fraction) - fee_rate * (capital * position_fraction)
                capital += gain
                position_open = False
                daily_results[current_date]["gain_loss"] += gain

                if gain_per > 0:
                    win += 1
                    current_loss_streak = 0
                else:
                    loss += 1
                    current_loss_streak += 1
                    if current_loss_streak > max_loss_streak:
                        max_loss_streak = current_loss_streak

                if gain_per > max_win:
                    max_win = gain_per
                if gain_per < max_loss:
                    max_loss = gain_per
                if capital < lowest_capital:
                    lowest_capital = capital

                # Classification of highest gain
                if 1 <= highest_gain_open * 100 < 2:
                    # print("gain1", pre_previous_item["Time1"])
                    gain_1_2_percent += 1
                elif 2 <= highest_gain_open * 100 < 4:
                    # print("gain2", pre_previous_item["Time1"])
                    gain_2_4_percent += 1
                elif highest_gain_open * 100 >= 4:
                    # print("gain4", pre_previous_item["Time1"])
                    gain_more_than_4_percent += 1
                highest_gain_open = 0  # Reset for the next position

                if enable_log:
                    print(
                        f"{token} Close {position_type} at {i} | {previous_item['Time1']} Gain %: {gain_per*100:.2f}%. Cap: {capital:.2f}",
                        "\n",
                    )
                continue

            if current_direction == -1 and previous_direction == 1:
                gain = gain_per * (capital * position_fraction) - fee_rate * (capital * position_fraction)
                capital += gain
                position_open = False
                daily_results[current_date]["gain_loss"] += gain
                if gain_per > 0:
                    win += 1
                    current_loss_streak = 0
                else:
                    loss += 1
                    current_loss_streak += 1
                    if current_loss_streak > max_loss_streak:
                        max_loss_streak = current_loss_streak

                if gain_per > max_win:
                    max_win = gain_per
                if gain_per < max_loss:
                    max_loss = gain_per
                if capital < lowest_capital:
                    lowest_capital = capital

                # Classification of highest gain
                if 1 <= highest_gain_open * 100 < 2:
                    # print("gain1", pre_previous_item["Time1"])
                    gain_1_2_percent += 1
                elif 2 <= highest_gain_open * 100 < 4:
                    # print("gain2", pre_previous_item["Time1"])
                    gain_2_4_percent += 1
                elif highest_gain_open * 100 >= 4:
                    # print("gain4", pre_previous_item["Time1"])
                    gain_more_than_4_percent += 1
                highest_gain_open = 0  # Reset for the next position

                if enable_log:
                    print(
                        f"{token} Close {position_type} at {i} | {previous_item['Time1']} Gain %: {gain_per*100:.2f}%. Cap: {capital:.2f}",
                        "\n",
                    )

        # Close short position
        elif position_open and position_type == "short":
            exit_price = previous_close
            gain_per = (entry_price - exit_price) / entry_price * leverage

            if gain_per <= stop_lost or gain_per >= tp:
                if gain_per >= tp:
                    gain_per = tp
                else:
                    gain_per = stop_lost
                    stop_lost_rate += 1

                gain = gain_per * (capital * position_fraction) - fee_rate * (capital * position_fraction)
                capital += gain
                position_open = False
                daily_results[current_date]["gain_loss"] += gain
                if gain_per > 0:
                    win += 1
                    current_loss_streak = 0
                else:
                    loss += 1
                    current_loss_streak += 1
                    if current_loss_streak > max_loss_streak:
                        max_loss_streak = current_loss_streak

                if gain_per > max_win:
                    max_win = gain_per
                if gain_per < max_loss:
                    max_loss = gain_per
                if capital < lowest_capital:
                    lowest_capital = capital

                # Classification of highest gain
                if 1 <= highest_gain_open * 100 < 2:
                    # print("gain1", pre_previous_item["Time1"])
                    gain_1_2_percent += 1
                elif 2 <= highest_gain_open * 100 < 4:
                    # print("gain2", pre_previous_item["Time1"])
                    gain_2_4_percent += 1
                elif highest_gain_open * 100 >= 4:
                    # print("gain4", pre_previous_item["Time1"])
                    gain_more_than_4_percent += 1
                highest_gain_open = 0  # Reset for the next position

                if enable_log:
                    print(
                        f"{token} Close {position_type} at {i} | {previous_item['Time1']} Gain %: {gain_per*100:.2f}%. Cap: {capital:.2f}",
                        "\n",
                    )
                continue

            if current_direction == 1 and previous_direction == -1:
                gain = gain_per * (capital * position_fraction) - fee_rate * (capital * position_fraction)
                capital += gain
                position_open = False
                daily_results[current_date]["gain_loss"] += gain
                if gain_per > 0:
                    win += 1
                    current_loss_streak = 0
                else:
                    loss += 1
                    current_loss_streak += 1
                    if current_loss_streak > max_loss_streak:
                        max_loss_streak = current_loss_streak

                if gain_per > max_win:
                    max_win = gain_per
                if gain_per < max_loss:
                    max_loss = gain_per
                if capital < lowest_capital:
                    lowest_capital = capital

                # Classification of highest gain
                if 1 <= highest_gain_open * 100 < 2:
                    # print("gain1", pre_previous_item["Time1"])
                    gain_1_2_percent += 1
                elif 2 <= highest_gain_open * 100 < 4:
                    # print("gain2", pre_previous_item["Time1"])
                    gain_2_4_percent += 1
                elif highest_gain_open * 100 >= 4:
                    # print("gain4", pre_previous_item["Time1"])
                    gain_more_than_4_percent += 1
                highest_gain_open = 0  # Reset for the next position

                if enable_log:
                    print(
                        f"{token} Close {position_type} at {i}  | {previous_item['Time1']} Gain %: {gain_per*100:.2f}% Cap: {capital:.2f}",
                        "\n",
                    )

        # Open position
        if not position_open:
            if pre_previous_direction == -1 and previous_direction == 1:
                if not check_time(item["Time1"]):
                    continue
                if not check_direction_15m_with_15m_ha(df_data, item["Time"], -1, 1):
                    continue
                entry_price = item["real_price_open"]
                position_open = True
                position_type = "long"
                long_opened += 1
                highest_gain_open = 0  # Reset for new position
                if enable_log:
                    print(f"{token} Open long at {i} {item['Time1']}")
            elif pre_previous_direction == 1 and previous_direction == -1:
                if not check_time(item["Time1"]):
                    continue
                if not check_direction_15m_with_15m_ha(df_data, item["Time"], 1, -1):
                    continue
                entry_price = item["real_price_open"]
                position_open = True
                position_type = "short"
                short_opened += 1
                highest_gain_open = 0  # Reset for new position
                if enable_log:
                    print(f"{token} Open short at {i} {item['Time1']}")

    final_capital = capital
    percentage_gain = ((final_capital - initial_capital) / initial_capital) * 100

    print("Win: ", win)
    print("Loss: ", loss)
    print("Win Rate: ", win / (win + loss) * 100)
    print("1% - 2%: ", gain_1_2_percent)
    print("2% - 4%: ", gain_2_4_percent)
    print("More than 4%: ", gain_more_than_4_percent)

    daily_results_list = []
    for date, results in daily_results.items():
        daily_results_list.append(
            {
                "date": date,
                "capital_start": results["capital_start"],
                "capital_end": results["capital_start"] + results["gain_loss"],
                "gain_loss": results["gain_loss"],
            }
        )

    tables = []
    for daily_result in daily_results_list:
        tables.append(
            [
                daily_result["date"],
                f"${daily_result['capital_start']:.2f}",
                f"${daily_result['capital_end']:.2f}",
                f"${daily_result['gain_loss']:.2f}",
            ]
        )
    if enable_log:
        print(
            tabulate.tabulate(
                tables,
                headers=[
                    "Date",
                    "Capital Start",
                    "Capital End",
                    "Gain/Loss",
                ],
            )
        )
    daily_win_rate = 0

    for daily_result in daily_results_list:
        if daily_result["gain_loss"] > 0:
            daily_win_rate += 1

    daily_win_rate = f"{(daily_win_rate / len(daily_results_list) * 100):.2f}% ({daily_win_rate}/{len(daily_results_list)}) days"

    return {
        "token": token,
        "initial_capital": initial_capital,
        "final_capital": final_capital,
        "percentage_gain": percentage_gain,
        "win_rate": win / (win + loss) * 100,
        "total_win": win,
        "total_loss": loss,
        "stop_lost_rate": f"{(stop_lost_rate / (win + loss)) * 100:.2f}% ({stop_lost_rate}/{win+loss})",
        "daily_win_rate": daily_win_rate,
        "max_win": max_win * 100,
        "max_loss": max_loss * 100,
        "lowest_capital": lowest_capital,
        "max_loss_streak": max_loss_streak,
        "1-2%": f"{gain_1_2_percent/(win+loss)*100:.2f}% ({gain_1_2_percent}/{win+loss})",
        "2-4%": f"{gain_2_4_percent/(win+loss)*100:.2f}% ({gain_2_4_percent}/{win+loss})",
        "more than 2%": f"{(gain_more_than_4_percent + gain_2_4_percent)/(win+loss)*100:.2f}% ({gain_more_than_4_percent + gain_2_4_percent}/{win+loss})",
        "more_than_4%": f"{gain_more_than_4_percent/(win+loss)*100:.2f}% ({gain_more_than_4_percent}/{win+loss})",
    }


with open("tokens.15m.txt", "r") as file:
    tokens = [line.strip() for line in file]

import tabulate

table1 = []
table2 = []
for token in tokens:
    data = run_trading_strategy(token, time_frame)
    formatted_initial_capital = f"${float(data['initial_capital']):,.2f}"
    formatted_final_capital = f"{float(data['final_capital']):,.2f}"
    formatted_percentage_gain = f"{float(data['percentage_gain']):,.2f}%"
    formatted_win_rate = f"{float(data['win_rate']):,.2f}% ({data['total_win']}/{data['total_win'] + data['total_loss']})"
    formatted_max_win = f"{float(data['max_win']):,.2f}%"
    formatted_max_loss = f"{float(data['max_loss']):,.2f}%"
    formatted_lowest_capital = f"{float(data['lowest_capital']):,.2f}"

    table1.append(
        [
            data["token"],
            formatted_initial_capital,
            formatted_final_capital,
            formatted_lowest_capital,
            formatted_percentage_gain,
            formatted_win_rate,
        ]
    )

    table2.append(
        [
            data["token"],
            data["stop_lost_rate"],
            data["daily_win_rate"],
            data["1-2%"],
            data["2-4%"],
            data["more than 2%"],
            data["more_than_4%"],
            formatted_max_win,
            formatted_max_loss,
            data["max_loss_streak"],
        ]
    )

# Sort table by "Final Capital" which is the third item in the sublist (index 2)
# table = sorted(table, key=lambda x: float(x[2].replace(",", "")), reverse=True)
print(
    f"\n\nTime Frame: {time_frame}\nBacktesting Results from 2024-06-26 to 2024-07-26.\nNo position open between (01:00 - 06:30 AM) \nLeverage: x{leverage}\nStop Loss: {stop_lost * 100}\nFee Rate: {fee_rate*100:.2f}%"
)
print(
    tabulate.tabulate(
        table1,
        headers=[
            "Token",
            "Initial Capital",
            "Final Capital",
            "Lowest Capital",
            "Percentage Gain",
            "Win Rate",
        ],
    )
)
print(
    tabulate.tabulate(
        table2,
        headers=[
            "Token",
            "Stop Loss Rate",
            "Daily Win Rate",
            "1-2%",
            "2-4%",
            "More than 2%",
            "More than 4%",
            "Max Win %",
            "Max Loss %",
            "Max Loss Streak",
        ],
    )
)
