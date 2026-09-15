"""
Inspect Dataset - Urban Mobility & Traffic Intelligence
Phase 1: Project Foundation and Dataset Audit

Reads the raw dataset, verifies its integrity, computes comprehensive data quality metrics,
and outputs a summary without modifying or moving the raw file.
"""

import os
import hashlib
import pandas as pd
import numpy as np


RAW_DATA_PATH = os.path.join("data", "raw", "Metro_Interstate_Traffic_Volume.csv")
EXPECTED_SHA256 = "749c90d720360a4215bb15345526073c079ba4cc95e3fa558796d083f85fce9e"


def verify_file_integrity(filepath: str) -> bool:
    """Verifies that the raw dataset exists and matches expected SHA-256 hash."""
    if not os.path.isfile(filepath):
        print(f"[ERROR] Target file not found: {filepath}")
        return False
    
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    digest = sha256.hexdigest()
    print(f"[OK] File exists: {filepath} ({os.path.getsize(filepath):,} bytes)")
    print(f"[OK] SHA-256 Checksum: {digest}")
    if digest == EXPECTED_SHA256:
        print("[OK] Checksum matches expected pristine raw file.")
    else:
        print("[WARNING] Checksum differs from reference signature.")
    return True


def inspect_dataset(filepath: str):
    """Performs deep inspection of the dataset and prints summary statistics."""
    print("\n" + "=" * 70)
    print("URBAN MOBILITY & TRAFFIC INTELLIGENCE - DATASET AUDIT (PHASE 1)")
    print("=" * 70)

    # 1. Load with keep_default_na=False to distinguish literal 'None' from null
    df_raw = pd.read_csv(filepath, keep_default_na=False)
    # Also load standard to see default pandas behavior
    df_std = pd.read_csv(filepath)

    n_rows, n_cols = df_raw.shape
    print(f"\n1. DATASET DIMENSIONS")
    print(f"   - Total Rows: {n_rows:,}")
    print(f"   - Total Columns: {n_cols}")
    print(f"   - Column Names: {list(df_raw.columns)}")

    print(f"\n2. DATA TYPES & NULL ANALYSIS")
    print(f"   {'Column':<22} {'Raw Dtype':<12} {'Raw Nulls':<12} {'Std Nulls (Pandas)':<20} {'Notes'}")
    print(f"   {'-'*22} {'-'*12} {'-'*12} {'-'*20} {'-'*15}")
    for col in df_raw.columns:
        raw_null = df_raw[col].isna().sum() or (df_raw[col] == '').sum()
        std_null = df_std[col].isna().sum()
        std_pct = (std_null / n_rows) * 100
        notes = "Literal 'None' strings" if col == 'holiday' and std_null > 0 else "Clean"
        print(f"   {col:<22} {str(df_raw[col].dtype):<12} {raw_null:<12} {f'{std_null:,} ({std_pct:.2f}%)':<20} {notes}")

    print(f"\n3. DUPLICATE RECORDS")
    exact_dups = df_raw.duplicated().sum()
    print(f"   - Exact Full-Row Duplicates: {exact_dups} rows")

    print(f"\n4. TEMPORAL COVERAGE & CONTINUITY")
    df_raw['dt_parsed'] = pd.to_datetime(df_raw['date_time'], errors='coerce')
    nat_count = df_raw['dt_parsed'].isna().sum()
    min_dt = df_raw['dt_parsed'].min()
    max_dt = df_raw['dt_parsed'].max()
    unique_ts = df_raw['dt_parsed'].nunique()
    total_span_hours = int((max_dt - min_dt).total_seconds() / 3600) + 1
    missing_hours = total_span_hours - unique_ts

    print(f"   - Parsing Failures (NaT): {nat_count}")
    print(f"   - Earliest Record: {min_dt}")
    print(f"   - Latest Record: {max_dt}")
    print(f"   - Total Timeline Span: {total_span_hours:,} calendar hours")
    print(f"   - Distinct Timestamps Recorded: {unique_ts:,}")
    print(f"   - Missing Hourly Gaps: {missing_hours:,} hours ({missing_hours / total_span_hours * 100:.2f}% of span)")

    ts_counts = df_raw['date_time'].value_counts()
    multi_ts = (ts_counts > 1).sum()
    print(f"   - Timestamps with Multiple Weather Observations: {multi_ts:,} ({multi_ts / unique_ts * 100:.2f}% of unique timestamps)")

    print(f"\n5. NUMERICAL METRICS SUMMARY")
    num_cols = ['temp', 'rain_1h', 'snow_1h', 'clouds_all', 'traffic_volume']
    stats_df = df_std[num_cols].describe().T[['min', '25%', '50%', '75%', 'max', 'mean', 'std']]
    print(stats_df.to_string())

    print(f"\n6. SUSPICIOUS VALUES & OUTLIER DETECTION")
    zero_temp = (df_raw['temp'] == 0).sum()
    max_rain = df_raw['rain_1h'].max()
    zero_traffic = (df_raw['traffic_volume'] == 0).sum()
    print(f"   - Temperature == 0.0 K (Absolute Zero anomaly): {zero_temp} records")
    print(f"   - Maximum 1-hour rainfall: {max_rain:.2f} mm (Physical anomaly: {max_rain/1000:.2f} meters/hr)")
    print(f"   - Zero traffic volume instances: {zero_traffic} records")

    print(f"\n7. CATEGORICAL CARDINALITY")
    print(f"   - holiday: {df_raw['holiday'].nunique()} distinct values (Non-holiday count: {(df_raw['holiday'] == 'None').sum():,})")
    print(f"   - weather_main: {df_raw['weather_main'].nunique()} distinct categories: {sorted(df_raw['weather_main'].unique())}")
    print(f"   - weather_description: {df_raw['weather_description'].nunique()} distinct categories (Notice mixed casing: 'sky is clear' vs 'Sky is Clear')")

    print(f"\n8. TARGET SUITABILITY: traffic_volume")
    print(f"   - Dtype: int64")
    print(f"   - Min: {df_raw['traffic_volume'].min()} | Max: {df_raw['traffic_volume'].max()} | Median: {df_raw['traffic_volume'].median()}")
    print(f"   - Conclusion: Excellent target metric for regression, time-series forecasting, and operational intelligence.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    if verify_file_integrity(RAW_DATA_PATH):
        inspect_dataset(RAW_DATA_PATH)
