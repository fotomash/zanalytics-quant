import pandas as pd
import numpy as np
from datetime import datetime
import os
import traceback

class DataProcessor:

    def __init__(self):
        self.data = None
        self.metadata = {}

    def load_data(self, filepath):
        """Load market data, specifically handling tab-separated formats and malformed files robustly."""
        try:
            # Attempt to read as tab-separated first
            df = pd.read_csv(filepath, sep='\t', engine='python')
            print(f"[DEBUG] Loaded columns: {df.columns.tolist()}")
            print(df.head(3))

            # If parsing failed and resulted in a single column, attempt to split
            if len(df.columns) == 1:
                # Try splitting on commas if tabs didn't work
                print("[INFO] Only one column detected. Trying comma separator...")
                df = pd.read_csv(filepath, sep=',', engine='python')
                print(f"[DEBUG] After comma split: {df.columns.tolist()}")
                print(df.head(3))
                # If still only one column, try splitting that column
                if len(df.columns) == 1:
                    df = df.iloc[:, 0].str.split('\t', expand=True)
                    new_header = df.iloc[0]
                    df = df[1:]
                    df.columns = new_header
                    df.reset_index(drop=True, inplace=True)

            # Standardize column names
            df.columns = [str(col).lower().strip() for col in df.columns]

            # Rename 'timestamp' to 'datetime' for consistency
            if 'timestamp' in df.columns:
                df.rename(columns={'timestamp': 'datetime'}, inplace=True)

            # Ensure required columns exist
            required_cols = ['datetime', 'open', 'high', 'low', 'close']
            if not all(col in df.columns for col in required_cols):
                raise ValueError(f"Data file must contain columns: {required_cols}. Found: {df.columns.tolist()}")

            # Handle volume - use 'tickvol' if 'volume' is 0 or not present
            if 'volume' not in df.columns or df['volume'].astype(float).sum() == 0:
                if 'tickvol' in df.columns:
                    print("Info: 'volume' column is empty or missing. Using 'tickvol' as volume source.")
                    # Always assign as 1D numeric Series, never DataFrame
                    df['volume'] = pd.to_numeric(df['tickvol'], errors='coerce')
                else:
                    print("Warning: No volume data found. Using 1 as a placeholder.")
                    df['volume'] = 1
            else:
                df['volume'] = pd.to_numeric(df['volume'], errors='coerce')

            # Convert data types safely
            df['datetime'] = pd.to_datetime(df['datetime'], errors='coerce')
            df.set_index('datetime', inplace=True)

            numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_cols:
                if col in df.columns:
                    # Defensive: only convert if Series (1D)
                    if isinstance(df[col], (pd.Series, list, np.ndarray)):
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    else:
                        print(f"[WARNING] Column '{col}' is not 1D and cannot be converted. Type: {type(df[col])}")

            # Clean up data
            df.dropna(inplace=True)
            df.sort_index(inplace=True)

            self.metadata = {
                'symbol': os.path.basename(filepath).split('_')[0],
                'start_date': df.index[0] if not df.empty else None,
                'end_date': df.index[-1] if not df.empty else None,
                'total_bars': len(df),
                'timeframe': self._detect_timeframe(df) if not df.empty else "Unknown"
            }

            self.data = df
            return df

        except Exception as e:
            tb = traceback.format_exc()
            raise Exception(f"Error loading data from {filepath}: {str(e)}\nTraceback:\n{tb}")

    def load_tick_data(self, filepath):
        """Load and process tick data from a CSV file."""
        try:
            # Load the data, assuming tab separation
            ticks_df = pd.read_csv(filepath, sep='\t', engine='python')

            # As before, handle the case where the header is part of the data
            if len(ticks_df.columns) == 1:
                ticks_df = ticks_df.iloc[:, 0].str.split('\t', expand=True)
                new_header = ticks_df.iloc[0]
                ticks_df = ticks_df[1:]
                ticks_df.columns = new_header
                ticks_df.reset_index(drop=True, inplace=True)

            # Standardize column names
            ticks_df.columns = [str(col).lower().strip() for col in ticks_df.columns]

            # Rename 'timestamp' to 'datetime'
            if 'timestamp' in ticks_df.columns:
                ticks_df.rename(columns={'timestamp': 'datetime'}, inplace=True)

            # Convert data types
            ticks_df['datetime'] = pd.to_datetime(ticks_df['datetime'])
            ticks_df.set_index('datetime', inplace=True)

            numeric_cols = ['bid', 'ask', 'last', 'volume', 'spread']
            for col in numeric_cols:
                if col in ticks_df.columns:
                    ticks_df[col] = pd.to_numeric(ticks_df[col], errors='coerce')

            # Clean up
            ticks_df.dropna(subset=['bid', 'ask'], inplace=True)
            ticks_df.sort_index(inplace=True)

            print(f"Successfully loaded and processed {len(ticks_df)} ticks from {filepath}.")
            return ticks_df

        except Exception as e:
            tb = traceback.format_exc()
            raise Exception(f"Error loading tick data from {filepath}: {str(e)}\nTraceback:\n{tb}")

    def _detect_timeframe(self, df):
        """Detect the timeframe of the data"""
        if len(df) < 2:
            return "Unknown"

        time_diffs = df.index[1:] - df.index[:-1]
        avg_diff = time_diffs.mean()
        minutes = avg_diff.total_seconds() / 60

        timeframe_map = {
            1: "M1", 5: "M5", 15: "M15", 30: "M30", 60: "H1",
            240: "H4", 1440: "D1", 10080: "W1"
        }

        closest_tf = min(timeframe_map.keys(), key=lambda x: abs(x - minutes))
        return timeframe_map[closest_tf]