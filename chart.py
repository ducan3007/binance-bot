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
        df.loc[:, "Time1"] = pd.to_datetime(df["Time1"])  # Ensure Time1 is datetime

        # Set index for mplfinance
        df.set_index("Time1", inplace=True, drop=True)

        # Prepare Heikin-Ashi data for plotting
        ha_candles = df[["Open", "High", "Low", "Close"]].copy()
        ha_candles = ha_candles.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"})
        ha_candles.dropna(inplace=True)

        # Define figure dimensions
        width = 13
        height = scale * width

        # Create figure and axis with custom background
        fig, ax = plt.subplots(figsize=(width, height), facecolor="#181a20")
        fig.patch.set_facecolor("#181a20")
        ax.set_facecolor("#181a20")

        # Define custom market colors
        wick = (0.7216, 0.7216, 0.7216, 0.78)
        if TIME_FRAME == "15m":
            wick = "inherit"
        mc = mpf.make_marketcolors(
            up="#11aa91",  # Green
            down="#fc3852",  # Red
            edge="inherit",
            wick=wick,
            volume="inherit",
        )

        # Apply custom style
        s = mpf.make_mpf_style(
            marketcolors=mc,
            facecolor="#181a20",
            edgecolor="#181a20",
        )

        # Prepare additional plots (ZLSMA and EMA lines)
        zlsma_34 = df["ZLSMA_34"].dropna()
        zlsma_50 = df["ZLSMA_50"].dropna()
        ema_15 = df["EMA_15"].dropna()
        ema_21 = df["EMA_21"].dropna()
        ema_34 = df["EMA_34"].dropna()
        ema_50 = df["EMA_50"].dropna()

        apds = [
            mpf.make_addplot(ema_15, color="#2962ff", width=0.7, ax=ax),
            mpf.make_addplot(ema_21, color="#2962ff", width=0.7, ax=ax),
            mpf.make_addplot(ema_34, color="#3179f5", width=0.7, ax=ax),
            mpf.make_addplot(zlsma_34, color="white", width=1, ax=ax),
            mpf.make_addplot(zlsma_50, color="yellow", width=1, ax=ax),
        ]
        if TIME_FRAME != "1h" and TIME_FRAME != "30m":
            apds.append(mpf.make_addplot(ema_50, color="#ab47bc", width=1.2, ax=ax))

        # Plot Heikin-Ashi candles
        mpf.plot(
            ha_candles,
            type="candle",
            style=s,
            ax=ax,
            datetime_format="%H:%M",
            xrotation=0,
            addplot=apds,
        )

        # Custom coloring based on previous close
        closes = ha_candles["close"].values
        green = "#11aa91"
        red = "#fc3852"
        # First candle defaults to green (no previous close); others based on condition
        colors = [green if i == 0 else (green if closes[i] > closes[i - 1] else red) for i in range(len(closes))]

        # Update wick colors (LineCollection)

        if TIME_FRAME == "15m":
            wick_collection = ax.collections[0]  # Wicks are the first collection
            wick_collection.set_colors(colors)

        border_collection = ax.collections[1]  # Bodies are the second collection
        border_collection.set_edgecolors(colors)
        border_collection.set_facecolors(colors)

        # Update candle body colors (Rectangle patches)
        for patch, color in zip(ax.patches, colors):
            patch.set_facecolor(color)
            patch.set_edgecolor(color)

        # Customize plot appearance
        # ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.2, color="gray")  # Uncomment if grid is desired
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")
        ax.tick_params(axis="x", colors="white")
        ax.tick_params(axis="y", colors="white")

        # Save the chart
        plt.savefig(image_path, bbox_inches="tight", facecolor="#181a20", dpi=400)
        plt.close(fig)

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
        {"tf": "15m", "view": 60, "mode": "heikin_ashi", "scale": 0.633},
        {"tf": "30m", "view": 70, "mode": "kline", "scale": 0.633},
    ],
    "15m": [
        {"tf": "30m", "view": 72, "mode": "heikin_ashi", "scale": 0.633},
        {"tf": "1h", "view": 48, "mode": "kline", "scale": 0.633},
    ],
    "1h": [
        {"tf": "1h", "view": 48, "mode": "heikin_ashi", "scale": 0.633},
        {"tf": "4h", "view": 30, "mode": "kline", "scale": 0.633},
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
