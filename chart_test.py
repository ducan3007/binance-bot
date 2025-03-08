import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from logger import logger

# Telegram Bot Credentials
TELEGRAM_BOT_TOKEN = "7565493265:AAFPnrLlqKtENz8O_slfXCwVwYHkOzTO9C8"
CHAT_ID = "-1002194508247"

# Load Data
df_data = pd.read_csv("t_DOGE_ce_15m_1.8_HA.csv")


def generate_chart(title, df: pd.DataFrame):
    try:
        image_path = f"heikin_ashi_scaled_{title}.png"
        df["Time1"] = pd.to_datetime(df["Time1"])  # Convert time column

        # Set index for mplfinance
        df.set_index("Time1", inplace=True)

        # Prepare data for plotting
        ha_candles = df[["Open", "High", "Low", "Close"]].copy()
        ha_candles.columns = ["open", "high", "low", "close"]  # Rename for mplfinance

        # ✅ Drop NaN rows to prevent plotting errors
        ha_candles.dropna(inplace=True)

        # Create figure and axis with fully #0c0e14 background
        fig, ax = plt.subplots(figsize=(10, 7), facecolor="#0c0e14")

        # Set entire canvas background to #0c0e14
        fig.patch.set_facecolor("#0c0e14")
        ax.set_facecolor("#0c0e14")

        # Define custom Heikin-Ashi colors
        mc = mpf.make_marketcolors(
            up="#11aa91",  # Green for bullish candles
            down="#fc3852",  # Red for bearish candles
            edge="inherit",
            wick="inherit",
            volume="inherit",
        )

        # Apply the custom style with a #0c0e14 background
        s = mpf.make_mpf_style(
            marketcolors=mc,
            facecolor="#0c0e14",  # Set background color to #0c0e14
            edgecolor="#0c0e14",  # Ensure edges blend with the background
        )

        # Plot Heikin-Ashi Candles with custom colors
        mpf.plot(
            ha_candles,
            type="candle",
            style=s,  # Apply custom styling
            ax=ax,
            datetime_format="%H:%M",
            xrotation=0,
        )

        # Enable grid with gray lines for visibility
        ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.2, color="gray")

        # Remove top and right borders (spines)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)

        # Change text color to white
        ax.text(
            0.02,
            0.98,
            f"{title}",
            transform=ax.transAxes,
            fontsize=15,
            fontweight="bold",
            verticalalignment="top",
            horizontalalignment="left",
            color="white",  # Change text color to white
        )

        # Set tick labels to white
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.tick_params(axis="x", colors="white")
        ax.tick_params(axis="y", colors="white")

        # Save the chart with #0c0e14 background
        plt.savefig(image_path, bbox_inches="tight", facecolor="#0c0e14")
        plt.close(fig)  # Free memory

        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        with open(image_path, "rb") as photo:
            import requests

            files = {"photo": photo}
            data = {"chat_id": CHAT_ID, "caption": f"📊 Chart {title}", "parse_mode": "HTML"}
            requests.post(url, files=files, data=data)

        return image_path
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return None


# Run the function
if __name__ == "__main__":
    generate_chart("DOGE", df_data)
