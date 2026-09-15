"""
Feature Engineering Pipeline for Time-Series Traffic Volume Forecasting
Urban Mobility & Traffic Intelligence - Phase 4

CRITICAL GUARANTEES:
1. No Artificial Continuity: Every lag is computed by looking up the EXACT historical timestamp.
   If the timestamp (t - k hours) is missing or unobserved, lag is NaN.
   Lags NEVER bridge across gaps or the 307-day sensor blackout.
2. Zero Future Leakage: Rolling features use closed='left' over physical time intervals,
   strictly excluding the current observation (t) and using only past values (< t).
3. Chronological Isolation: Temporal splitting ensures Train < Validation < Test with zero
   data shuffling or cross-split contamination.
"""

import os
import json
import logging
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

PROCESSED_DATA_PATH = os.path.join("data", "processed", "traffic_cleaned.csv")
FEATURES_DATA_PATH = os.path.join("data", "processed", "traffic_features.csv")

# Weather severity hierarchy for consistent ordinal encoding
WEATHER_SEVERITY_ORDER = {
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


def build_exact_lags(df: pd.DataFrame, lag_hours: list = None) -> pd.DataFrame:
    """
    Builds lag features by looking up EXACT timestamps in the observed historical series.
    If date_time - lag_hours does not exist in the index, the value is set to NaN.
    Guarantees no lag relationship bridges across multi-hour missing gaps or the 307-day blackout.
    """
    if lag_hours is None:
        lag_hours = [1, 2, 3, 4, 6, 12, 24, 48, 168]

    volume_series = df.set_index("date_time")["traffic_volume"]
    lag_dict = {}

    for k in lag_hours:
        target_dt = df["date_time"] - pd.Timedelta(hours=k)
        lag_dict[f"traffic_lag_{k}h"] = target_dt.map(volume_series).values

    return pd.DataFrame(lag_dict, index=df.index)


def build_past_only_rolling_stats(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds past-only rolling statistics using physical time windows with closed='left'.
    closed='left' strictly excludes the current observation (t), so only past values [t - W, t)
    are included. Physical time windows ensure gaps larger than W produce NaN (zero blackout bleed).
    """
    s = df.set_index("date_time")["traffic_volume"].sort_index()

    roll_dict = {}

    # 6-hour window: strictly [t - 6h, t)
    roll_6 = s.rolling("6h", closed="left")
    roll_dict["traffic_roll_mean_6h"] = roll_6.mean().values
    roll_dict["traffic_roll_std_6h"] = roll_6.std().values
    roll_dict["traffic_roll_min_6h"] = roll_6.min().values
    roll_dict["traffic_roll_max_6h"] = roll_6.max().values

    # 24-hour window: strictly [t - 24h, t)
    roll_24 = s.rolling("24h", closed="left")
    roll_dict["traffic_roll_mean_24h"] = roll_24.mean().values
    roll_dict["traffic_roll_std_24h"] = roll_24.std().values
    roll_dict["traffic_roll_min_24h"] = roll_24.min().values
    roll_dict["traffic_roll_max_24h"] = roll_24.max().values

    # 168-hour (7-day) window: strictly [t - 168h, t)
    roll_168 = s.rolling("168h", closed="left")
    roll_dict["traffic_roll_mean_168h"] = roll_168.mean().values
    roll_dict["traffic_roll_std_168h"] = roll_168.std().values

    return pd.DataFrame(roll_dict, index=df.index)


def engineer_feature_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """
    Executes the full feature engineering pipeline on the processed dataset.
    Returns an enriched DataFrame with target, lags, rolling stats, temporal, and weather features.
    """
    logger.info("Starting feature engineering pipeline...")
    df = df.sort_values("date_time").reset_index(drop=True).copy()

    # 1. Exact-timestamp traffic lags
    logger.info("Computing exact timestamp lags (1h, 2h, 3h, 4h, 6h, 12h, 24h, 48h, 168h)...")
    lags_df = build_exact_lags(df)

    # 2. Past-only rolling window statistics
    logger.info("Computing past-only rolling statistics (closed='left' over 6h, 24h, 168h)...")
    rolling_df = build_past_only_rolling_stats(df)

    # 3. Cyclical Temporal Encodings
    logger.info("Computing cyclical sine/cosine temporal features...")
    temporal_dict = {
        "hour_sin": np.sin(2.0 * np.pi * df["hour"] / 24.0),
        "hour_cos": np.cos(2.0 * np.pi * df["hour"] / 24.0),
        "dow_sin": np.sin(2.0 * np.pi * df["day_of_week"] / 7.0),
        "dow_cos": np.cos(2.0 * np.pi * df["day_of_week"] / 7.0),
        "month_sin": np.sin(2.0 * np.pi * (df["month"] - 1.0) / 12.0),
        "month_cos": np.cos(2.0 * np.pi * (df["month"] - 1.0) / 12.0),
        "day_of_month": df["day"],
    }
    temporal_df = pd.DataFrame(temporal_dict, index=df.index)

    # 4. Weather encodings
    logger.info("Encoding weather severity rank and atmospheric features...")
    weather_severity = df["weather_main"].map(WEATHER_SEVERITY_ORDER).fillna(1).astype(int)

    # Combine everything
    base_features = [
        "date_time",
        "traffic_volume",  # Primary forecasting target
        "hour",
        "day_of_week",
        "month",
        "is_weekend",
        "is_holiday",
        "is_morning_rush_hour",
        "is_evening_rush_hour",
        "temp_celsius",
        "rain_1h",
        "snow_1h",
        "clouds_all",
        "weather_event_count",
    ]

    out_df = pd.concat([
        df[base_features],
        pd.DataFrame({"weather_severity_rank": weather_severity}, index=df.index),
        temporal_df,
        lags_df,
        rolling_df
    ], axis=1)

    logger.info(f"Feature engineering complete. Total rows: {len(out_df)}, Total columns: {len(out_df.columns)}")
    return out_df


def split_chronological(
    df: pd.DataFrame,
    train_end: str = "2017-09-30 23:00:00",
    val_end: str = "2018-03-31 23:00:00"
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Partitions the dataset into Train, Validation, and Test sets based strictly on timestamp boundaries.
    Never shuffles. Asserts strictly chronological progression with zero split overlap.
    """
    train_end_dt = pd.Timestamp(train_end)
    val_end_dt = pd.Timestamp(val_end)

    train_df = df[df["date_time"] <= train_end_dt].copy()
    val_df = df[(df["date_time"] > train_end_dt) & (df["date_time"] <= val_end_dt)].copy()
    test_df = df[df["date_time"] > val_end_dt].copy()

    # Integrity assertions
    assert not train_df.empty, "Train partition cannot be empty."
    assert not val_df.empty, "Validation partition cannot be empty."
    assert not test_df.empty, "Test partition cannot be empty."

    assert train_df["date_time"].max() < val_df["date_time"].min(), "Train overlaps with Validation!"
    assert val_df["date_time"].max() < test_df["date_time"].min(), "Validation overlaps with Test!"

    logger.info(f"Train split:      {train_df['date_time'].min()} to {train_df['date_time'].max()} ({len(train_df):,} rows)")
    logger.info(f"Validation split: {val_df['date_time'].min()} to {val_df['date_time'].max()} ({len(val_df):,} rows)")
    logger.info(f"Test split:       {test_df['date_time'].min()} to {test_df['date_time'].max()} ({len(test_df):,} rows)")

    return train_df, val_df, test_df


def get_feature_columns() -> list[str]:
    """Returns the ordered list of predictive feature column names."""
    return [
        # Calendar & Indicators
        "hour",
        "day_of_week",
        "month",
        "day_of_month",
        "is_weekend",
        "is_holiday",
        "is_morning_rush_hour",
        "is_evening_rush_hour",
        "hour_sin",
        "hour_cos",
        "dow_sin",
        "dow_cos",
        "month_sin",
        "month_cos",
        # Atmospheric
        "temp_celsius",
        "rain_1h",
        "snow_1h",
        "clouds_all",
        "weather_event_count",
        "weather_severity_rank",
        # Exact Lags
        "traffic_lag_1h",
        "traffic_lag_2h",
        "traffic_lag_3h",
        "traffic_lag_4h",
        "traffic_lag_6h",
        "traffic_lag_12h",
        "traffic_lag_24h",
        "traffic_lag_48h",
        "traffic_lag_168h",
        # Past-Only Rolling Statistics
        "traffic_roll_mean_6h",
        "traffic_roll_std_6h",
        "traffic_roll_min_6h",
        "traffic_roll_max_6h",
        "traffic_roll_mean_24h",
        "traffic_roll_std_24h",
        "traffic_roll_min_24h",
        "traffic_roll_max_24h",
        "traffic_roll_mean_168h",
        "traffic_roll_std_168h",
    ]


if __name__ == "__main__":
    if not os.path.exists(PROCESSED_DATA_PATH):
        raise FileNotFoundError(f"Processed dataset not found at {PROCESSED_DATA_PATH}. Run src/clean_dataset.py first.")

    raw_clean_df = pd.read_csv(PROCESSED_DATA_PATH, parse_dates=["date_time"])
    feat_df = engineer_feature_pipeline(raw_clean_df)

    feat_df.to_csv(FEATURES_DATA_PATH, index=False)
    logger.info(f"Saved engineered features to: {FEATURES_DATA_PATH}")

    train_df, val_df, test_df = split_chronological(feat_df)
    print("\nFeature Engineering Summary:")
    print(f"Total Records: {len(feat_df)}")
    print(f"Feature Columns: {len(get_feature_columns())}")
    print(f"Train Rows: {len(train_df)} | Val Rows: {len(val_df)} | Test Rows: {len(test_df)}")
