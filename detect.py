import pandas as pd
import numpy as np

def detect_sharp_peaks_and_troughs(csv_file, start_time, end_time):
    # Load the CSV file
    df = pd.read_csv(csv_file)
    
    # Convert the 'Time' column to datetime
    df['Time'] = pd.to_datetime(df['Time'])
    
    # Filter data within the specified time range
    df_filtered = df[(df['Time'] >= start_time) & (df['Time'] <= end_time)]
    
    # Calculate the difference between consecutive ZLSMA values
    df_filtered['Diff'] = df_filtered['ZLSMA'].diff()
    
    # Find sharp tops (local maxima) and bottoms (local minima)
    sharp_tops = df_filtered[(df_filtered['Diff'].shift(1) > 0) & (df_filtered['Diff'] < 0)]
    sharp_bottoms = df_filtered[(df_filtered['Diff'].shift(1) < 0) & (df_filtered['Diff'] > 0)]
    
    return sharp_tops, sharp_bottoms

# Example usage
csv_file = 'path_to_your_csv_file.csv'  # Replace with your CSV file path
start_time = '2024-04-23 00:00'
end_time = '2024-04-24 00:00'

sharp_tops, sharp_bottoms = detect_sharp_peaks_and_troughs(csv_file, start_time, end_time)

print("Sharp Tops:")
print(sharp_tops)

print("\nSharp Bottoms:")
print(sharp_bottoms)
