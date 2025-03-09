import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from logger import logger
import zlma
from PIL import Image
import os


def generate_chart(title, PAIR, TIME_FRAME):
    try:
        image_path = f"{title}.png"
        df = zlma.fetch_zlsma(PAIR, TIME_FRAME)
        df.loc[:, "Time1"] = pd.to_datetime(df["Time1"])  # Should already be datetime64[ns]
        
        # Set index for mplfinance without triggering inference warning
        df.set_index("Time1", inplace=True, drop=True)

        # Prepare data for plotting
        ha_candles = df[["Open", "High", "Low", "Close"]].copy()
        ha_candles = ha_candles.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"})

        # ✅ Drop NaN rows to prevent plotting errors
        ha_candles.dropna(inplace=True)

        # Create figure and axis with fully #101015 background
        fig, ax = plt.subplots(figsize=(10, 7), facecolor="#101015")

        # Set entire canvas background to #101015
        fig.patch.set_facecolor("#101015")
        ax.set_facecolor("#101015")

        # Define custom Heikin-Ashi colors
        mc = mpf.make_marketcolors(
            up="#11aa91",  # Green for bullish candles
            down="#fc3852",  # Red for bearish candles
            edge="inherit",
            wick="inherit",
            volume="inherit",
        )

        # Apply the custom style with a #101015 background
        s = mpf.make_mpf_style(
            marketcolors=mc,
            facecolor="#101015",  # Set background color to #101015
            edgecolor="#101015",  # Ensure edges blend with the background
        )

        # Prepare ZLSMA lines for plotting
        zlsma_34 = df["ZLSMA_34"].dropna()  # White line
        zlsma_50 = df["ZLSMA_50"].dropna()  # Yellow line

        # Define additional plots for ZLSMA lines, explicitly passing the axis (ax)
        apds = [
            mpf.make_addplot(zlsma_34, color="white", width=0.8, ax=ax),
            mpf.make_addplot(zlsma_50, color="yellow", width=1.4, ax=ax),
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

        # Save the chart with higher DPI for better quality
        plt.savefig(image_path, bbox_inches="tight", facecolor="#101015", dpi=300)
        plt.close(fig)  # Free memory

        return image_path
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return None


def concatenate_images(image1_path, image2_path, output_path):
    try:
        # Open the two images
        img1 = Image.open(image1_path)
        img2 = Image.open(image2_path)

        # Get dimensions of both images
        width1, height1 = img1.size
        width2, height2 = img2.size

        # Calculate the dimensions of the new image
        # Width will be sum of both widths
        # Height will be the maximum height of the two images
        new_width = width1 + width2
        new_height = max(height1, height2)

        # Create a new blank image with the calculated dimensions
        new_image = Image.new("RGB", (new_width, new_height))

        # Paste first image at position (0,0)
        new_image.paste(img1, (0, 0))

        # Paste second image right next to first image
        new_image.paste(img2, (width1, 0))

        # Save the concatenated image
        new_image.save(output_path)
        print(f"Images successfully concatenated and saved as {output_path}")

    except Exception as e:
        print(f"An error occurred: {str(e)}")


PARI_MAP = {
    "5m": ["5m", "15m"],
    "15m": ["15m", "30m"],
    "1h": ["1h", "4h"],
}


def get_charts(title, PAIR, TIME_FRAME):
    try:
        image1 = generate_chart(f"{title}_{TIME_FRAME}", PAIR, TIME_FRAME)
        image2 = generate_chart(f"{title}_{PARI_MAP[TIME_FRAME][1]}", PAIR, PARI_MAP[TIME_FRAME][1])

        if image1 and image2:
            output_path = f"{title}_concatenated.png"
            concatenate_images(image1, image2, output_path)
            os.remove(image1)
            os.remove(image2)
            return output_path

    except Exception as e:
        logger.error(f"Error getting charts: {e}")
        return None
