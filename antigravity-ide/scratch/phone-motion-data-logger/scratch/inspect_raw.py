import os
import glob
import pandas as pd
import numpy as np

data_dir = r"c:\Users\Keerthana N\.gemini\antigravity-ide\scratch\phone-motion-data-logger\data"
csv_files = glob.glob(os.path.join(data_dir, "*.csv"))

print(f"Found {len(csv_files)} CSV files in {data_dir}:\n")

for filepath in sorted(csv_files):
    filename = os.path.basename(filepath)
    print("="*80)
    print(f"FILE: {filename}")
    print("="*80)
    
    # Read header and first few rows
    df = pd.read_csv(filepath, nrows=100)
    print(f"Columns ({len(df.columns)}): {list(df.columns)}")
    
    # Check total rows
    total_rows = sum(1 for _ in open(filepath, 'r', encoding='utf-8', errors='ignore')) - 1
    print(f"Total Rows: {total_rows}")
    
    # Check stream types if available
    if 'stream_type' in df.columns:
        full_df = pd.read_csv(filepath, usecols=['stream_type'])
        stream_counts = full_df['stream_type'].value_counts().to_dict()
        print(f"Stream Type Breakdown: {stream_counts}")
    elif 'phone_timestamp' in df.columns:
        print("Format: Flattened Web Telemetry Format")
        
    print("\nFirst 3 rows:")
    print(df.head(3).T)
    print("\n")
