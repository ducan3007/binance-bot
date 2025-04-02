import pandas as pd
import numpy as np

def calculate_ema(series, period):
    """
    Calculate Exponential Moving Average (EMA) for a given series and period.
    
    Args:
        series (pd.Series): Input series (e.g., Close prices)
        period (int): EMA period (e.g., 34)
    
    Returns:
        pd.Series: EMA values
    """
    return series.ewm(span=period, adjust=False).mean()

def detect_trend(df, N=10, k=0.7):
    """
    Detect market trend (up, down, sideways) based on OHLC data.
    
    Args:
        df (pd.DataFrame): DataFrame with 'Open', 'High', 'Low', 'Close' columns
        N (int): Window size for trend analysis (default: 10)
        k (float): Threshold proportion for trend confirmation (default: 0.7)
    
    Returns:
        pd.DataFrame: DataFrame with added 'trend' column
    """
    # Copy the DataFrame to avoid modifying the original
    df = df.copy()
    
    # Calculate EMA_34 from Close prices if not provided
    if 'EMA_34' not in df.columns:
        df['EMA_34'] = calculate_ema(df['Close'], 34)
    
    # Initialize trend column with 'sideway' as default
    df['trend'] = 'sideway'
    
    # Define the threshold for increases/decreases
    threshold = int(np.ceil(k * (N - 1)))
    
    # Iterate over the DataFrame starting from the N-th bar
    for i in range(N - 1, len(df)):
        # Extract the last N EMA_34 values (including current bar)
        ema_slice = df['EMA_34'].iloc[i - N + 1:i + 1]
        
        # Calculate differences and drop NaN (first diff is NaN)
        diffs = ema_slice.diff().dropna()
        
        # Count increases and decreases
        increases = (diffs > 0).sum()
        decreases = (diffs < 0).sum()
        
        # Classify trend
        if increases >= threshold:
            df.loc[i, 'trend'] = 'up'
        elif decreases >= threshold:
            df.loc[i, 'trend'] = 'down'
        # Else, remains 'sideway'
    
    return df

# Example usage
if __name__ == "__main__":
    # Load the CSV file (adjust path as needed)
    file_path = 'zlma.csv'
    try:
        df = pd.read_csv(file_path)
        
        # Ensure required columns are present
        required_cols = {'Open', 'High', 'Low', 'Close'}
        if not required_cols.issubset(df.columns):
            raise ValueError("DataFrame must contain 'Open', 'High', 'Low', 'Close' columns")
        
        # Detect trends
        df_with_trend = detect_trend(df, N=10, k=0.7)
        
        # Display results
        print("DataFrame with Trend:")
        print(df_with_trend[['Time', 'Close', 'EMA_34', 'trend']].tail(20))
        
        # Optionally save to CSV
        df_with_trend.to_csv('data_with_trend.csv', index=False)
        print("Results saved to 'data_with_trend.csv'")
        
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"Error: {e}")