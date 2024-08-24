import pandas as pd
from datetime import datetime, timedelta

leverage = 2
fee_rate = 0.0035
position_fraction = 1.00
stop_lost = -0.06
tp = 99


mode = ""

time_frame_ha_check = False

is_zlma_check = True

enable_log = True

time_frame = "30m"

time_frame_seconds_map = {
    "5m": 60 * 5,
    "15m": 60 * 15,
    "30m": 60 * 30,
    "1h": 60 * 60,
    "2h": 60 * 60 * 2,
    "4h": 60 * 60 * 4,
}

seconds = time_frame_seconds_map[time_frame]

start_date = "2024-04-01 00:00"
start_date_dt = datetime.strptime(start_date, "%Y-%m-%d %H:%M")

x = 32
y = 92
length = 32

start_back_test_time_dt = start_date_dt + timedelta(seconds=seconds * (y + (length - x) * 2))
start_back_test_time = int(start_back_test_time_dt.timestamp())

print("start_back_test_time", start_back_test_time)


def check_time(time1):
    time_object = datetime.strptime(time1, "%Y-%m-%d %H:%M")
    current_time = time_object.time()
    start_time = datetime.strptime("01:15", "%H:%M").time()
    end_time = datetime.strptime("06:00", "%H:%M").time()
    if start_time <= current_time <= end_time:
        return False
    return True


def check_direction_with_ha(df_ha, time, pre_direction, direction, seconds=900, tf="15m"):
    if df_ha is None:
        return True

    # Find the previous, current, and next 15m_ha candle rows
    pre_ha_candle = df_ha[df_ha["Time"] == (time - seconds)]
    current_ha_candle = df_ha[df_ha["Time"] == time]
    next_ha_candle = df_ha[df_ha["Time"] == (time + seconds)]

    # Check if the direction matches
    if not pre_ha_candle.empty and not current_ha_candle.empty:
        if pre_ha_candle.iloc[0]["direction"] == pre_direction and current_ha_candle.iloc[0]["direction"] == direction:
            print(
                f"Check Previous {tf} and Current {tf} direction match",
                pre_ha_candle.iloc[0]["Time1"],
                current_ha_candle.iloc[0]["Time1"],
            )
            return True

    if not current_ha_candle.empty and not next_ha_candle.empty:
        if current_ha_candle.iloc[0]["direction"] == pre_direction and next_ha_candle.iloc[0]["direction"] == direction:
            print(
                f"Check Current {tf} and Next {tf} direction match",
                current_ha_candle.iloc[0]["Time1"],
                next_ha_candle.iloc[0]["Time1"],
            )
            return True

    return False


def run_trading_strategy(token, time_frame):
    if mode == "ha":
        data = pd.read_csv(f"{token}_ce_{time_frame}_ha.csv")
    else:
        data = pd.read_csv(f"{token}_ce_{time_frame}.csv")

    if time_frame_ha_check:
        df_ha = pd.read_csv(f"{token}_ce_{time_frame}_ha.csv")
    else:
        df_ha = None

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
    price_retrace_entry = {
        "2024-04-02 02:30": True,
    }

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

    highest_loss_open = 0  # To track highest loss while position is open
    loss_1_2_percent = 0
    loss_2_4_percent = 0
    loss_more_than_4_percent = 0

    print(f"Processing token: {token}")

    for i in range(2, len(data)):
        item = data.iloc[i]
        current_time = item["Time"]

        if is_zlma_check and current_time < start_back_test_time:
            continue

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
                current_lost = (current_low - entry_price) / entry_price * leverage
            elif position_type == "short":
                current_gain = (entry_price - current_low) / entry_price * leverage
                current_lost = (entry_price - current_high) / entry_price * leverage

            if current_gain > highest_gain_open:
                highest_gain_open = current_gain

            if current_lost < highest_loss_open:
                highest_loss_open = current_gain

        # Close long position
        if position_open and position_type == "long":
            exit_price = previous_close
            gain_per = ((exit_price - entry_price) / entry_price) * leverage

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

                # Classification of highest loss
                if -1 >= highest_loss_open * 100 > -2:
                    print("loss1", pre_previous_item["Time1"])
                    loss_1_2_percent += 1
                elif -2 >= highest_loss_open * 100 > -4:
                    print("loss2", pre_previous_item["Time1"])
                    loss_2_4_percent += 1
                elif highest_loss_open * 100 <= -4:
                    print("loss4", pre_previous_item["Time1"])
                    loss_more_than_4_percent += 1

                # Classification of highest gain
                if 1 <= highest_gain_open * 100 < 2:
                    print("gain1", pre_previous_item["Time1"])
                    gain_1_2_percent += 1
                elif 2 <= highest_gain_open * 100 < 4:
                    print("gain2", pre_previous_item["Time1"])
                    gain_2_4_percent += 1
                elif highest_gain_open * 100 >= 4:
                    print("gain4", pre_previous_item["Time1"])
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

                # Classification of highest loss
                if -1 >= highest_loss_open * 100 > -2:
                    print("loss1", pre_previous_item["Time1"])
                    loss_1_2_percent += 1
                elif -2 >= highest_loss_open * 100 > -4:
                    print("loss2", pre_previous_item["Time1"])
                    loss_2_4_percent += 1
                elif highest_loss_open * 100 <= -4:
                    print("loss4", pre_previous_item["Time1"])
                    loss_more_than_4_percent += 1

                # Classification of highest gain
                if 1 <= highest_gain_open * 100 < 2:
                    print("gain1", pre_previous_item["Time1"])
                    gain_1_2_percent += 1
                elif 2 <= highest_gain_open * 100 < 4:
                    print("gain2", pre_previous_item["Time1"])
                    gain_2_4_percent += 1
                elif highest_gain_open * 100 >= 4:
                    print("gain4", pre_previous_item["Time1"])
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

                # Classification of highest loss
                if -1 >= highest_loss_open * 100 > -2:
                    print("loss1", pre_previous_item["Time1"])
                    loss_1_2_percent += 1
                elif -2 >= highest_loss_open * 100 > -4:
                    print("loss2", pre_previous_item["Time1"])
                    loss_2_4_percent += 1
                elif highest_loss_open * 100 <= -4:
                    print("loss4", pre_previous_item["Time1"])
                    loss_more_than_4_percent += 1

                # Classification of highest gain
                if 1 <= highest_gain_open * 100 < 2:
                    print("gain1", pre_previous_item["Time1"])
                    gain_1_2_percent += 1
                elif 2 <= highest_gain_open * 100 < 4:
                    print("gain2", pre_previous_item["Time1"])
                    gain_2_4_percent += 1
                elif highest_gain_open * 100 >= 4:
                    print("gain4", pre_previous_item["Time1"])
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

                # Classification of highest loss
                if -1 >= highest_loss_open * 100 > -2:
                    print("loss1", pre_previous_item["Time1"])
                    loss_1_2_percent += 1
                elif -2 >= highest_loss_open * 100 > -4:
                    print("loss2", pre_previous_item["Time1"])
                    loss_2_4_percent += 1
                elif highest_loss_open * 100 <= -4:
                    print("loss4", pre_previous_item["Time1"])
                    loss_more_than_4_percent += 1

                # Classification of highest gain
                if 1 <= highest_gain_open * 100 < 2:
                    print("gain1", pre_previous_item["Time1"])
                    gain_1_2_percent += 1
                elif 2 <= highest_gain_open * 100 < 4:
                    print("gain2", pre_previous_item["Time1"])
                    gain_2_4_percent += 1
                elif highest_gain_open * 100 >= 4:
                    print("gain4", pre_previous_item["Time1"])
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
                if time_frame_ha_check and not check_direction_with_ha(df_ha, item["Time"], -1, 1, seconds, time_frame):
                    continue

                if is_zlma_check and not ((previous_item["Open"] > previous_item["ZLSMA"]) or (item["Open"] > previous_item["ZLSMA"])):
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
                if time_frame_ha_check and not check_direction_with_ha(df_ha, item["Time"], 1, -1, seconds, time_frame):
                    continue

                if is_zlma_check and not (previous_item["Open"] < previous_item["ZLSMA"] or (item["Open"] < previous_item["ZLSMA"])):
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
        "-1-2%": f"{loss_1_2_percent/(win+loss)*100:.2f}% ({loss_1_2_percent}/{win+loss})",
        "-2-4%": f"{loss_2_4_percent/(win+loss)*100:.2f}% ({loss_2_4_percent}/{win+loss})",
        "more_than-4%": f"{loss_more_than_4_percent/(win+loss)*100:.2f}% ({loss_more_than_4_percent}/{win+loss})",
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
            data["-1-2%"],
            data["-2-4%"],
            data["more_than-4%"],
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
            "-1-2%",
            "-2-4%",
            "More than -4%",
            "Max Win %",
            "Max Loss %",
            "Max Loss Streak",
        ],
    )
)
