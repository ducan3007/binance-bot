import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from logger import logger
import zlma
from PIL import Image
import os
from datetime import datetime

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
        if TIME_FRAME != "1h":
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

def concatenate_images(image_paths, output_path, direction="vertical"):
    try:
        images = [Image.open(path) for path in image_paths]
        if not images:
            raise ValueError("No images provided for concatenation")

        if direction.lower() == "vertical":
            max_width = max(img.width for img in images)
            total_height = sum(img.height for img in images)
            new_image = Image.new("RGB", (max_width, total_height), color="#181a20")
            y_offset = 0
            for img in images:
                new_image.paste(img, (0, y_offset))
                y_offset += img.height
        elif direction.lower() == "horizontal":
            total_width = sum(img.width for img in images)
            max_height = max(img.height for img in images)
            new_image = Image.new("RGB", (total_width, max_height), color="#181a20")
            x_offset = 0
            for img in images:
                new_image.paste(img, (x_offset, 0))
                x_offset += img.width
        else:
            raise ValueError("Direction must be 'vertical' or 'horizontal'")

        new_image.save(output_path)
        print(f"Images successfully concatenated and saved as {output_path}")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

PARI_MAP = {
    "5m": [
        {"tf": "15m", "view": 60, "mode": "heikin_ashi", "scale": 0.633},
        {"tf": "30m", "view": 70, "mode": "kline", "scale": 0.633},
        {"tf": "1h", "view": 40, "mode": "kline", "scale": 0.633},
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

def get_charts(title, PAIR, TIME_FRAME, signal, time1):
    try:
        items = PARI_MAP[TIME_FRAME]
        image_paths = []

        for item in items:
            tf = item["tf"]
            view = item["view"]
            mode = item["mode"]
            scale = item["scale"]
            chart_title = f"{TIME_FRAME}_{title}_{tf}"
            image_path = generate_chart(chart_title, PAIR, tf, view, mode, scale)
            if image_path:
                image_paths.append(image_path)

        if image_paths:
            create_time_ns = datetime.now().timestamp()

            if TIME_FRAME == "5m" and len(image_paths) >= 2:
                prefix_temp = f"static_temp/{TIME_FRAME}_{title}_"
                os.system(f"rm {prefix_temp}*")  # Clean up previous files
                output_path_temp = f"{prefix_temp}{signal}_{time1}_{create_time_ns}.png"
                concatenate_images(image_paths[:2], output_path_temp, direction="vertical")

            prefix = f"static/{TIME_FRAME}_{title}_"
            os.system(f"rm {prefix}*")
            output_path = f"{prefix}{signal}_{time1}_{create_time_ns}.png"
            concatenate_images(image_paths, output_path, direction="vertical")

            for path in image_paths:
                os.remove(path)

            if TIME_FRAME == "5m":
                return output_path_temp

            return output_path
        return None
    except Exception as e:
        logger.error(f"Error getting charts: {e}")
        return None