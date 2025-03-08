import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
from logger import logger
import zlma


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
        plt.savefig(image_path, bbox_inches="tight", facecolor="#0c0e14", dpi=300)
        plt.close(fig)  # Free memory

        return image_path
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return None
