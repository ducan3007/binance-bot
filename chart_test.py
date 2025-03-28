import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from logger import logger
import zlma
from PIL import Image
import os


def generate_chart(title, PAIR, TIME_FRAME, view, mode, scale=0.7):
    try:
        image_path = f"{title}.png"
        df = zlma.fetch_zlsma(PAIR, TIME_FRAME, view, mode)
        df.loc[:, "Time1"] = pd.to_datetime(df["Time1"])  # Should already be datetime64[ns]

        # Set index for mplfinance without triggering inference warning
        df.set_index("Time1", inplace=True, drop=True)

        # Prepare data for plotting
        ha_candles = df[["Open", "High", "Low", "Close"]].copy()
        ha_candles = ha_candles.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"})

        # ✅ Drop NaN rows to prevent plotting errors
        ha_candles.dropna(inplace=True)

        # Define width and height where H = 1.5 * W
        width = 12  # You can adjust this base width as needed
        height = scale * width  # Height is 1.5 times the width

        # Create figure and axis with fully #181a20 background
        fig, ax = plt.subplots(figsize=(width, height), facecolor="#181a20")

        # Set entire canvas background to #181a20
        fig.patch.set_facecolor("#181a20")
        ax.set_facecolor("#181a20")

        # Define custom Heikin-Ashi colors
        wick = (0.7216, 0.7216, 0.7216, 0.80)
        if TIME_FRAME == "5m":
            wick = "inherit"
        mc = mpf.make_marketcolors(
            up="#11aa91",  # Green for bullish candles
            down="#fc3852",  # Red for bearish candles
            edge="inherit",  # Edges inherit candle color
            wick=wick,
            volume="inherit",
        )

        # Apply the custom style with a #181a20 background
        s = mpf.make_mpf_style(
            marketcolors=mc,
            facecolor="#181a20",  # Set background color to #181a20
            edgecolor="#181a20",  # Ensure edges blend with the background
        )

        # Prepare ZLSMA lines for plotting
        zlsma_34 = df["ZLSMA_34"].dropna()  # White line
        zlsma_50 = df["ZLSMA_50"].dropna()  # Yellow line
        ema_21 = df["EMA_21"].dropna()  # Light blue line
        ema_34 = df["EMA_34"].dropna()  # Blue line
        ema_50 = df["EMA_50"].dropna()  # Purple line

        # Define additional plots for ZLSMA lines, explicitly passing the axis (ax)
        apds = [
            mpf.make_addplot(ema_21, color="#5b9cf6", width=1.2, ax=ax),
            mpf.make_addplot(ema_34, color="#2962ff", width=1.5, ax=ax),
            mpf.make_addplot(ema_50, color="#ab47bc", width=1.5, ax=ax),
            mpf.make_addplot(zlsma_34, color="white", width=1.5, ax=ax),
            mpf.make_addplot(zlsma_50, color="yellow", width=1.5, ax=ax),
        ]

        # Plot Heikin-Ashi Candles with custom colors and additional ZLSMA lines
        mpf.plot(
            ha_candles,
            type="candle",
            style=s,  # Apply custom styling
            ax=ax,
            datetime_format="%H:%M",
            xrotation=0,
            addplot=apds,  # Add ZLSMA lines
        )

        # Enable grid with gray lines for visibility
        # ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.2, color="gray")

        # Remove top and right borders (spines)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)

        # Set tick labels to white
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.tick_params(axis="x", colors="white")
        ax.tick_params(axis="y", colors="white")

        # Save the chart with higher DPI for better quality
        plt.savefig(image_path, bbox_inches="tight", facecolor="#181a20", dpi=400)
        plt.close(fig)  # Free memory

        return image_path
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return None


def concatenate_images(image1_path, image2_path, output_path, direction="right"):
    try:
        # Open the two images
        img1 = Image.open(image1_path)
        img2 = Image.open(image2_path)

        # Get dimensions of both images
        width1, height1 = img1.size
        width2, height2 = img2.size

        # Calculate new dimensions based on direction
        if direction.lower() == "right":
            new_width = width1 + width2
            new_height = max(height1, height2)
            new_image = Image.new("RGB", (new_width, new_height))
            new_image.paste(img1, (0, 0))
            new_image.paste(img2, (width1, 0))

        elif direction.lower() == "left":
            new_width = width1 + width2
            new_height = max(height1, height2)
            new_image = Image.new("RGB", (new_width, new_height))
            new_image.paste(img2, (0, 0))
            new_image.paste(img1, (width2, 0))

        elif direction.lower() == "top":
            new_width = max(width1, width2)
            new_height = height1 + height2
            new_image = Image.new("RGB", (new_width, new_height))
            new_image.paste(img2, (0, 0))
            new_image.paste(img1, (0, height2))

        elif direction.lower() == "bottom":
            new_width = max(width1, width2)
            new_height = height1 + height2
            new_image = Image.new("RGB", (new_width, new_height))
            new_image.paste(img1, (0, 0))
            new_image.paste(img2, (0, height1))

        else:
            raise ValueError("Direction must be 'top', 'left', 'bottom', or 'right'")

        # Save the concatenated image
        new_image.save(output_path)
        print(f"Images successfully concatenated and saved as {output_path}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")


PARI_MAP = {
    "5m": [
        {"tf": "15m", "view": 48, "mode": "kline", "scale": 0.7},
        {"tf": "1h", "view": 36, "mode": "kline", "scale": 0.7},
    ],
    "15m": [
        {"tf": "30m", "view": 72, "mode": "heikin_ashi", "scale": 0.7},
        {"tf": "1h", "view": 48, "mode": "kline", "scale": 0.7},
    ],
    "1h": [
        {"tf": "1h", "view": 48, "mode": "heikin_ashi", "scale": 0.7},
        {"tf": "4h", "view": 30, "mode": "kline", "scale": 0.7},
    ],
}

from datetime import datetime


def get_charts(title, PAIR, TIME_FRAME, signal, time1):
    try:
        tf1 = PARI_MAP[TIME_FRAME][0]
        tf2 = PARI_MAP[TIME_FRAME][1]
        tftf1 = tf1["tf"]
        tftf2 = tf2["tf"]
        view1 = tf1["view"]
        view2 = tf2["view"]
        mode1 = tf1["mode"]
        mode2 = tf2["mode"]
        scale1 = tf1["scale"]
        scale2 = tf2["scale"]

        image1 = generate_chart(f"{TIME_FRAME}_{title}_{tftf1}", PAIR, tftf1, view1, mode1, scale1)
        image2 = generate_chart(f"{TIME_FRAME}_{title}_{tftf2}", PAIR, tftf2, view2, mode2, scale2)

        if image1 and image2:
            # remove file with prefix
            prefix = f"static/{TIME_FRAME}_{title}_"
            os.system(f"rm {prefix}*")
            # nanoseconds
            create_time_ns = datetime.now().timestamp()
            output_path = f"{prefix}{signal}_{time1}_{create_time_ns}.png"
            concatenate_images(image1, image2, output_path, direction="bottom")
            os.remove(image1)
            os.remove(image2)
            return output_path

    except Exception as e:
        logger.error(f"Error getting charts: {e}")
        return None


if __name__ == "__main__":
    title = "XRP"
    PAIR = "XRPUSDT"
    TIME_FRAME = "5m"
    get_charts(title, PAIR, TIME_FRAME, "BUY", "10:15")
    print("Done")
