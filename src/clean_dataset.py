"""
Data Cleaning & Feature Engineering Pipeline
Urban Mobility & Traffic Intelligence - Phase 2

This script executes the reproducible cleaning and feature engineering pipeline:
1. Ingests raw data preserving literal 'None' in holiday.
2. Standardizes schema to snake_case.
3. Removes exact duplicate records (17 rows).
4. Saves intermediate staging dataset to data/interim/traffic_staged.csv.
5. Handles sensor dropouts (temp == 0.0 K) and physical precipitation anomalies.
6. Normalizes categorical text casing.
7. Deterministically consolidates multi-observation timestamps using a domain-informed
   Weather Severity Hierarchy to establish a strict 1-row-per-hour grain.
8. Engineers rich temporal, calendar, and rush-hour features.
9. Exports final analytical table to data/processed/traffic_cleaned.csv.
"""

import os
import sys
import hashlib
import numpy as np
import pandas as pd

# Path configuration
RAW_PATH = os.path.join("data", "raw", "Metro_Interstate_Traffic_Volume.csv")
INTERIM_PATH = os.path.join("data", "interim", "traffic_staged.csv")
PROCESSED_PATH = os.path.join("data", "processed", "traffic_cleaned.csv")
LOG_PATH = os.path.join("reports", "cleaning_decisions.md")

# Weather Severity Ranking (Dominant condition for traffic operations)
WEATHER_SEVERITY_RANK = {
    "Thunderstorm": 11,
    "Squall": 10,
    "Snow": 9,
    "Rain": 8,
    "Drizzle": 7,
    "Fog": 6,
    "Mist": 5,
    "Haze": 4,
    "Smoke": 3,
    "Clouds": 2,
    "Clear": 1
}


def load_raw_dataset(filepath: str) -> pd.DataFrame:
    """Loads raw dataset preserving string 'None' and parsing datetimes."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Raw CSV not found at {filepath}")
    
    print(f"[INGEST] Reading raw dataset from: {filepath}")
    df = pd.read_csv(filepath, keep_default_na=False)
    print(f"[INGEST] Raw records loaded: {len(df):,} rows, {len(df.columns)} columns")
    return df


def standardize_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Ensures consistent snake_case naming and types."""
    df = df.copy()
    df.columns = [col.strip().lower() for col in df.columns]
    
    # Cast types
    df['temp'] = pd.to_numeric(df['temp'], errors='coerce')
    df['rain_1h'] = pd.to_numeric(df['rain_1h'], errors='coerce')
    df['snow_1h'] = pd.to_numeric(df['snow_1h'], errors='coerce')
    df['clouds_all'] = pd.to_numeric(df['clouds_all'], errors='coerce').astype(int)
    df['traffic_volume'] = pd.to_numeric(df['traffic_volume'], errors='coerce').astype(int)
    df['date_time'] = pd.to_datetime(df['date_time'], format='%Y-%m-%d %H:%M:%S')
    
    return df


def clean_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizes string trimming and text casing."""
    df = df.copy()
    
    # Trim whitespace
    df['holiday'] = df['holiday'].str.strip()
    df['weather_main'] = df['weather_main'].str.strip()
    df['weather_description'] = df['weather_description'].str.strip()
    
    # Standardize casing in weather_description ('Sky is Clear' -> 'sky is clear', 'SQUALLS' -> 'squalls')
    df['weather_description'] = df['weather_description'].str.lower()
    
    return df


def remove_exact_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Detects and drops exact full-row duplicate records."""
    initial_len = len(df)
    exact_dups = df.duplicated().sum()
    df_dedup = df.drop_duplicates().copy()
    print(f"[DEDUP] Identified and removed {exact_dups} exact full-row duplicates.")
    print(f"[DEDUP] Records remaining: {len(df_dedup):,} (from {initial_len:,})")
    return df_dedup


def handle_outliers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Addresses physical anomalies and sensor failures:
    - temp == 0.0 K (10 records): Imputed using linear time-series interpolation.
    - rain_1h == 9831.30 mm (1 record): Capped at max legitimate historical precipitation (55.63 mm).
    - traffic_volume == 0 (2 records): Retained as documented road closure events.
    """
    df = df.copy()
    
    # Sort temporally to allow valid interpolation
    df = df.sort_values(['date_time', 'weather_main']).reset_index(drop=True)
    
    # 1. Temperature Outlier (0.0 Kelvin sensor dropout)
    zero_temp_mask = df['temp'] == 0.0
    zero_temp_count = zero_temp_mask.sum()
    if zero_temp_count > 0:
        print(f"[OUTLIER] Detected {zero_temp_count} records with temp == 0.0 K. Applying linear interpolation...")
        df.loc[zero_temp_mask, 'temp'] = np.nan
        df['temp'] = df['temp'].interpolate(method='linear')
    
    # 2. Extreme Rain Outlier (9831.30 mm on 2016-07-11)
    rain_outlier_mask = df['rain_1h'] > 100.0
    rain_outlier_count = rain_outlier_mask.sum()
    if rain_outlier_count > 0:
        max_valid_rain = df.loc[~rain_outlier_mask, 'rain_1h'].max()
        print(f"[OUTLIER] Detected {rain_outlier_count} record with rain_1h > 100mm ({df.loc[rain_outlier_mask, 'rain_1h'].values[0]}mm).")
        print(f"[OUTLIER] Capping rain_1h anomaly to maximum legitimate observation: {max_valid_rain:.2f} mm.")
        df.loc[rain_outlier_mask, 'rain_1h'] = max_valid_rain
        
    return df


def consolidate_hourly_grain(df: pd.DataFrame) -> pd.DataFrame:
    """
    Consolidates multiple weather reports for the same hour into a single hourly record.
    Rule:
    - traffic_volume: Identical across all rows for the hour.
    - holiday: Identical across all rows for the hour.
    - temp: Mean of recorded temperatures during the hour.
    - rain_1h: Maximum recorded precipitation (peak intensity).
    - snow_1h: Maximum recorded snowfall.
    - clouds_all: Mean cloud coverage rounded to nearest integer.
    - weather_main & weather_description: Dominant condition selected using WEATHER_SEVERITY_RANK.
    - weather_event_count: Total distinct weather observations logged for that hour.
    """
    print("[GRAIN] Consolidating multi-observation timestamps into strict 1-row-per-hour grain...")
    
    # Assign numerical severity rank for aggregation
    df['severity_rank'] = df['weather_main'].map(WEATHER_SEVERITY_RANK).fillna(0)
    
    def aggregate_hour(group: pd.DataFrame) -> pd.Series:
        # Dominant weather row is the one with the highest severity rank
        dominant_row = group.sort_values('severity_rank', ascending=False).iloc[0]
        
        return pd.Series({
            'holiday': group['holiday'].iloc[0],
            'temp': round(group['temp'].mean(), 2),
            'rain_1h': round(group['rain_1h'].max(), 2),
            'snow_1h': round(group['snow_1h'].max(), 2),
            'clouds_all': int(round(group['clouds_all'].mean())),
            'weather_main': dominant_row['weather_main'],
            'weather_description': dominant_row['weather_description'],
            'traffic_volume': group['traffic_volume'].iloc[0],
            'weather_event_count': len(group)
        })
    
    hourly_df = df.groupby('date_time', as_index=False).apply(aggregate_hour, include_groups=False)
    
    print(f"[GRAIN] Consolidating completed. Resulting unique hourly records: {len(hourly_df):,}")
    return hourly_df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Generates temporal, calendar, rush-hour, and meteorological features."""
    print("[ENGINEER] Generating derived features...")
    df = df.copy()
    
    dt = df['date_time'].dt
    
    # Temporal Coordinates
    df['year'] = dt.year
    df['month'] = dt.month
    df['day'] = dt.day
    df['hour'] = dt.hour
    df['day_of_week'] = dt.dayofweek  # 0 = Monday, 6 = Sunday
    df['day_name'] = dt.day_name()
    df['month_name'] = dt.month_name()
    df['week_of_year'] = dt.isocalendar().week.astype(int)
    
    # Binary Indicators
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    df['is_holiday'] = (df['holiday'] != 'None').astype(int)
    
    # Rush Hour Definitions:
    # Non-holiday weekdays:
    # Morning rush: 06:00 to 09:00 (hours 6, 7, 8, 9)
    # Evening rush: 15:00 to 18:00 (hours 15, 16, 17, 18)
    is_weekday = df['is_weekend'] == 0
    is_workday = is_weekday & (df['is_holiday'] == 0)
    
    df['is_morning_rush_hour'] = (is_workday & df['hour'].isin([6, 7, 8, 9])).astype(int)
    df['is_evening_rush_hour'] = (is_workday & df['hour'].isin([15, 16, 17, 18])).astype(int)
    
    # Temperature Unit Conversions
    df['temp_celsius'] = round(df['temp'] - 273.15, 2)
    df['temp_fahrenheit'] = round((df['temp'] - 273.15) * 9 / 5 + 32, 2)
    
    # Sort chronologically
    df = df.sort_values('date_time').reset_index(drop=True)
    
    print(f"[ENGINEER] Total features in processed dataset: {len(df.columns)}")
    return df


def run_pipeline():
    """Executes the complete end-to-end cleaning and feature engineering pipeline."""
    print("=" * 70)
    print("STARTING PHASE 2 DATA CLEANING & FEATURE ENGINEERING PIPELINE")
    print("=" * 70)
    
    # Step 1: Load Raw
    df_raw = load_raw_dataset(RAW_PATH)
    
    # Step 2: Standardize Schema
    df_std = standardize_schema(df_raw)
    
    # Step 3: Clean Categoricals
    df_cat = clean_categoricals(df_std)
    
    # Step 4: Remove Exact Duplicates
    df_dedup = remove_exact_duplicates(df_cat)
    
    # Step 5: Save Staged Dataset to Interim
    os.makedirs(os.path.dirname(INTERIM_PATH), exist_ok=True)
    df_dedup.to_csv(INTERIM_PATH, index=False)
    print(f"[EXPORT] Saved interim staged dataset: {INTERIM_PATH} ({len(df_dedup):,} rows)")
    
    # Step 6: Outlier Handling
    df_clean = handle_outliers(df_dedup)
    
    # Step 7: Consolidate to Strict Hourly Grain
    df_hourly = consolidate_hourly_grain(df_clean)
    
    # Step 8: Feature Engineering
    df_final = engineer_features(df_hourly)
    
    # Step 9: Export Processed Dataset
    os.makedirs(os.path.dirname(PROCESSED_PATH), exist_ok=True)
    df_final.to_csv(PROCESSED_PATH, index=False)
    print(f"[EXPORT] Saved processed clean dataset: {PROCESSED_PATH} ({len(df_final):,} rows, {len(df_final.columns)} cols)")
    print("=" * 70)
    print("PHASE 2 CLEANING PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    run_pipeline()
