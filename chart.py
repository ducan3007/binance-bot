import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from logger import logger
import zlma
from PIL import Image
import os
from datetime import datetime
import numpy as np


def generate_chart(title, PAIR, TIME_FRAME, view, mode, scale=0.7):
    try:
        image_path = f"{title}.png"
        df = zlma.fetch_zlsma(PAIR, TIME_FRAME, view, mode)
        df.loc[:, "Time1"] = pd.to_datetime(df["Time1"])  # Ensure Time1 is datetime

        # Set index for mplfinance
        df.set_index("Time1", inplace=True, drop=True)

        # Define the condition for coloring EMA lines
        condition = df["EMA_15"] < df["EMA_34"]

        # Create segmented series for each EMA line
        # Red where EMA_15 < EMA_34, NaN elsewhere
        ema_15_red = df["EMA_15"].where(condition, other=np.nan)
        ema_21_red = df["EMA_21"].where(condition, other=np.nan)
        ema_34_red = df["EMA_34"].where(condition, other=np.nan)

        # Green where EMA_15 >= EMA_34, NaN elsewhere
        ema_15_green = df["EMA_15"].where(~condition, other=np.nan)
        ema_21_green = df["EMA_21"].where(~condition, other=np.nan)
        ema_34_green = df["EMA_34"].where(~condition, other=np.nan)

        # Prepare Heikin-Ashi candlestick data
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
        ema_50 = df["EMA_50"].dropna() if "EMA_50" in df.columns else None

        # List of additional plots
        apds = [
            mpf.make_addplot(ema_15_red, color="#fc3852", width=0.7, ax=ax),
            mpf.make_addplot(ema_15_green, color="#11aa91", width=0.7, ax=ax),
            mpf.make_addplot(ema_21_red, color="#fc3852", width=0.7, ax=ax),
            mpf.make_addplot(ema_21_green, color="#11aa91", width=0.7, ax=ax),
            mpf.make_addplot(ema_34_red, color="#fc3852", width=0.8, ax=ax),
            mpf.make_addplot(ema_34_green, color="#11aa91", width=0.8, ax=ax),
            mpf.make_addplot(zlsma_34, color="white", width=1, ax=ax),
            mpf.make_addplot(zlsma_50, color="yellow", width=1, ax=ax),
        ]

        # Add EMA_50 if timeframe is not 1h
        if TIME_FRAME != "1h" and ema_50 is not None:
            apds.append(mpf.make_addplot(ema_50, color="#ab47bc", width=1.2, ax=ax))

        # Plot the candlestick chart
        mpf.plot(
            ha_candles,
            type="candle",
            style=s,
            ax=ax,
            datetime_format="%H:%M",
            xrotation=0,
            addplot=apds,
        )

        # Custom coloring for candlesticks based on close price
        closes = ha_candles["close"].values
        green = "#11aa91"
        red = "#fc3852"
        # First candle is green; others depend on previous close
        colors = [green if i == 0 else (green if closes[i] > closes[i - 1] else red) for i in range(len(closes))]

        # Update wick colors for 15m timeframe
        if TIME_FRAME == "15m" or TIME_FRAME == "5m":
            wick_collection = ax.collections[0]  # Wicks
            wick_collection.set_colors(colors)

        # Update candle body and border colors
        border_collection = ax.collections[1]  # Bodies
        border_collection.set_edgecolors(colors)
        border_collection.set_facecolors(colors)

        for patch, color in zip(ax.patches, colors):
            patch.set_facecolor(color)
            patch.set_edgecolor(color)

        # Customize chart appearance
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.tick_params(axis="x", colors="white")
        ax.tick_params(axis="y", colors="white")

        # Save the chart
        plt.savefig(image_path, bbox_inches="tight", facecolor="#181a20", dpi=400)
        plt.close(fig)

        return image_path
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return None


def concatenate_images_list(images, direction="horizontal"):
    """Concatenate a list of images either horizontally or vertically and return the result."""
    if not images:
        raise ValueError("No images provided for concatenation")

    if direction.lower() == "horizontal":
        total_width = sum(img.width for img in images)
        max_height = max(img.height for img in images)
        new_image = Image.new("RGB", (total_width, max_height), color="#181a20")
        x_offset = 0
        for img in images:
            new_image.paste(img, (x_offset, 0))
            x_offset += img.width
    elif direction.lower() == "vertical":
        max_width = max(img.width for img in images)
        total_height = sum(img.height for img in images)
        new_image = Image.new("RGB", (max_width, total_height), color="#181a20")
        y_offset = 0
        for img in images:
            new_image.paste(img, (0, y_offset))
            y_offset += img.height
    else:
        raise ValueError("Direction must be 'vertical' or 'horizontal'")

    return new_image


def concatenate_images_2d(image_paths_2d, output_path):
    """Concatenate images from a 2D array: horizontally within rows, then vertically across rows."""
    try:
        # Step 1: Process each row by concatenating images horizontally
        row_images = []
        for row in image_paths_2d:
            if not row:  # Skip empty rows
                continue
            # Open all images in the current row
            images = [Image.open(path) for path in row]
            if not images:  # Skip if no valid images in row
                continue
            # Concatenate images in this row horizontally
            row_image = concatenate_images_list(images, direction="horizontal")
            row_images.append(row_image)

        # Check if there are any row images to concatenate
        if not row_images:
            raise ValueError("No images to concatenate")

        # Step 2: Concatenate all row images vertically
        final_image = concatenate_images_list(row_images, direction="vertical")

        # Save the final image to the specified output path
        final_image.save(output_path)
        print(f"Images successfully concatenated and saved as {output_path}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")


PARI_MAP = {
    "5m": [
        [
            {"tf": "1h", "view": 48, "mode": "kline", "scale": 0.633},
        ],
        [
            # {"tf": "5m", "view": 60, "mode": "heikin_ashi", "scale": 0.633},
            # {"tf": "15m", "view": 70, "mode": "heikin_ashi", "scale": 0.633},
            {"tf": "30m", "view": 48, "mode": "kline", "scale": 0.633},
        ],
    ],
    "15m": [
        [{"tf": "30m", "view": 72, "mode": "heikin_ashi", "scale": 0.633}],
        [{"tf": "1h", "view": 48, "mode": "kline", "scale": 0.633}],
    ],
    "1h": [
        [{"tf": "1h", "view": 48, "mode": "heikin_ashi", "scale": 0.633}],
        [{"tf": "4h", "view": 30, "mode": "kline", "scale": 0.633}],
    ],
}


def get_charts(title, PAIR, TIME_FRAME, signal, time1):
    try:
        items = PARI_MAP[TIME_FRAME]
        image_paths = []
        for sublist in items:
            row_paths = []
            for item in sublist:
                tf = item["tf"]
                view = item["view"]
                mode = item["mode"]
                scale = item["scale"]
                chart_title = f"{TIME_FRAME}_{title}_{tf}"
                image_path = generate_chart(chart_title, PAIR, tf, view, mode, scale)
                if image_path:
                    row_paths.append(image_path)
            image_paths.append(row_paths)

        if image_paths:
            create_time_ns = datetime.now().timestamp()

            if TIME_FRAME == "5m" and len(image_paths) >= 2:
                prefix_temp = f"static_temp/{TIME_FRAME}_{title}_"
                os.system(f"rm {prefix_temp}*")  # Clean up previous files
                output_path_temp = f"{prefix_temp}{signal}_{time1}_{create_time_ns}.png"
                output_path_temp2 = f"{prefix_temp}{signal}_{time1}_{create_time_ns}_2.png"
                concatenate_images_2d([[image_paths[0][0]]], output_path_temp)
                concatenate_images_2d([[image_paths[1][0]]], output_path_temp2)

            prefix = f"static/{TIME_FRAME}_{title}_"
            os.system(f"rm {prefix}*")
            output_path = f"{prefix}{signal}_{time1}_{create_time_ns}.png"
            concatenate_images_2d(image_paths, output_path)

            for path in image_paths:
                for img_path in path:
                    if os.path.exists(img_path):
                        print(f"Removing temporary image: {img_path}")
                        os.remove(img_path)

            if TIME_FRAME == "5m":
                return [output_path_temp, output_path_temp2]

            return [output_path]
        return None
    except Exception as e:
        logger.error(f"Error getting charts: {e}, traceback: {e.__traceback__}")
        return None