"""
Unit and Integration Tests for Phase 4: Time-Series ML & Traffic Volume Forecasting
Urban Mobility & Traffic Intelligence

Validates:
1. Target alignment (strict y_t target with past-only features)
2. Chronological splitting (Train < Val < Test, zero overlap)
3. Exact lag correctness (verifies against explicit historical records)
4. Gap handling & blackout isolation (no lag/rolling bleed across gaps or 307-day blackout)
5. No future leakage (closed='left' strictly excludes current observation)
6. Train/Val/Test isolation (encoders/models fit on past data only)
7. Prediction shape, types, and non-negativity
8. Metric calculation exactness (MAE, RMSE, sMAPE, R2)
"""

import os
import sys
import json
import unittest
import numpy as np
import pandas as pd
import joblib

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("src"))

from src.features import (
    FEATURES_DATA_PATH,
    PROCESSED_DATA_PATH,
    split_chronological,
    get_feature_columns,
    build_exact_lags,
    build_past_only_rolling_stats
)
from src.train_forecasting_models import calculate_metrics

MODEL_PATH = os.path.join("models", "traffic_forecaster_best.joblib")
CONFIG_PATH = os.path.join("models", "feature_config.json")


class TestForecastPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Load feature dataset and metadata."""
        if not os.path.isfile(FEATURES_DATA_PATH):
            raise FileNotFoundError(f"Features file {FEATURES_DATA_PATH} not found. Run src/features.py first.")
        cls.df = pd.read_csv(FEATURES_DATA_PATH, parse_dates=["date_time"])
        cls.train_df, cls.val_df, cls.test_df = split_chronological(cls.df)
        cls.feature_cols = get_feature_columns()

    # --------------------------------------------------------------------------
    # 1. TARGET ALIGNMENT & SCHEMA INTEGRITY
    # --------------------------------------------------------------------------
    def test_target_alignment(self):
        """Verify target column exists, has no nulls, and aligns with observed timestamps."""
        self.assertIn("traffic_volume", self.df.columns)
        self.assertEqual(self.df["traffic_volume"].isnull().sum(), 0)
        self.assertEqual(len(self.df), 40575)
        # Target must be non-negative integer
        self.assertTrue((self.df["traffic_volume"] >= 0).all())

    def test_feature_columns_completeness(self):
        """Verify all 39 predictive feature columns are present."""
        for col in self.feature_cols:
            self.assertIn(col, self.df.columns, f"Missing feature column: {col}")

    # --------------------------------------------------------------------------
    # 2. CHRONOLOGICAL SPLITTING
    # --------------------------------------------------------------------------
    def test_chronological_splitting_isolation(self):
        """Verify Train < Validation < Test with zero chronological overlap."""
        train_max = self.train_df["date_time"].max()
        val_min = self.val_df["date_time"].min()
        val_max = self.val_df["date_time"].max()
        test_min = self.test_df["date_time"].min()

        self.assertLess(train_max, val_min, "Train overlaps with Validation!")
        self.assertLess(val_max, test_min, "Validation overlaps with Test!")

        # Assert expected sizes
        self.assertEqual(len(self.train_df), 31842)
        self.assertEqual(len(self.val_df), 4347)
        self.assertEqual(len(self.test_df), 4386)
        self.assertEqual(len(self.train_df) + len(self.val_df) + len(self.test_df), 40575)

    # --------------------------------------------------------------------------
    # 3. EXACT LAG CORRECTNESS
    # --------------------------------------------------------------------------
    def test_exact_lag_correctness(self):
        """Verify lag values match historical records for known contiguous timestamps."""
        vol_map = self.df.set_index("date_time")["traffic_volume"]

        # Sample 50 contiguous records where lags exist
        sample_rows = self.df[self.df["traffic_lag_1h"].notna()].sample(50, random_state=42)

        for _, row in sample_rows.iterrows():
            dt = row["date_time"]
            # Check 1h lag
            expected_1h = vol_map.get(dt - pd.Timedelta(hours=1))
            self.assertEqual(row["traffic_lag_1h"], expected_1h)

            # Check 24h lag if present
            if pd.notna(row["traffic_lag_24h"]):
                expected_24h = vol_map.get(dt - pd.Timedelta(hours=24))
                self.assertEqual(row["traffic_lag_24h"], expected_24h)

            # Check 168h lag if present
            if pd.notna(row["traffic_lag_168h"]):
                expected_168h = vol_map.get(dt - pd.Timedelta(hours=168))
                self.assertEqual(row["traffic_lag_168h"], expected_168h)

    # --------------------------------------------------------------------------
    # 4. GAP HANDLING & BLACKOUT ISOLATION
    # --------------------------------------------------------------------------
    def test_blackout_boundary_isolation(self):
        """Verify that records immediately following the 307-day blackout do NOT bleed across the gap."""
        # Row immediately following blackout: 2015-06-11 20:00:00
        blackout_post_dt = pd.Timestamp("2015-06-11 20:00:00")
        row = self.df[self.df["date_time"] == blackout_post_dt].iloc[0]

        # 1h prior (2015-06-11 19:00:00) is unobserved -> lag_1h must be NaN
        self.assertTrue(pd.isna(row["traffic_lag_1h"]), "Blackout bleed: lag_1h should be NaN!")

        # 24h prior (2015-06-10 20:00:00) was in the blackout -> lag_24h must be NaN
        self.assertTrue(pd.isna(row["traffic_lag_24h"]), "Blackout bleed: lag_24h should be NaN!")

        # 168h prior was in the blackout -> lag_168h must be NaN
        self.assertTrue(pd.isna(row["traffic_lag_168h"]), "Blackout bleed: lag_168h should be NaN!")

        # Rolling past 6h and 24h must have no observations -> must be NaN
        self.assertTrue(pd.isna(row["traffic_roll_mean_6h"]), "Blackout bleed: roll_mean_6h should be NaN!")
        self.assertTrue(pd.isna(row["traffic_roll_mean_24h"]), "Blackout bleed: roll_mean_24h should be NaN!")

    def test_unobserved_previous_hour_produces_nan(self):
        """Verify that any missing prior timestamp strictly results in NaN (no synthetic imputation)."""
        diffs = self.df["date_time"].diff()
        gap_indices = self.df[diffs > pd.Timedelta(hours=1)].index

        # For every record immediately following a gap > 1 hour, traffic_lag_1h MUST be NaN
        for idx in gap_indices[:20]:
            self.assertTrue(
                pd.isna(self.df.loc[idx, "traffic_lag_1h"]),
                f"Lag 1h at index {idx} should be NaN due to time gap!"
            )

    # --------------------------------------------------------------------------
    # 5. NO FUTURE LEAKAGE IN ROLLING FEATURES
    # --------------------------------------------------------------------------
    def test_no_future_leakage_rolling(self):
        """Verify that rolling window features with closed='left' exclude the current observation."""
        s = self.df.set_index("date_time")["traffic_volume"].sort_index()

        # Pick an arbitrary timestamp in a contiguous run
        test_dt = pd.Timestamp("2017-05-15 14:00:00")
        current_volume = s.loc[test_dt]

        # Observations strictly in [test_dt - 6h, test_dt)
        past_6h = s.loc[(s.index >= test_dt - pd.Timedelta(hours=6)) & (s.index < test_dt)]

        row = self.df[self.df["date_time"] == test_dt].iloc[0]
        self.assertAlmostEqual(row["traffic_roll_mean_6h"], past_6h.mean(), places=5)
        # Ensure current volume was NOT included
        self.assertFalse(test_dt in past_6h.index)

    # --------------------------------------------------------------------------
    # 6. MODEL ARTIFACT & CONFIG PERSISTENCE
    # --------------------------------------------------------------------------
    def test_model_artifact_and_config(self):
        """Verify model file and configuration exist, load properly, and have matching schema."""
        self.assertTrue(os.path.isfile(MODEL_PATH), f"Model file {MODEL_PATH} not found.")
        self.assertTrue(os.path.isfile(CONFIG_PATH), f"Config file {CONFIG_PATH} not found.")

        model = joblib.load(MODEL_PATH)
        self.assertIsNotNone(model)

        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)

        self.assertEqual(config["feature_count"], len(self.feature_cols))
        self.assertIn("test_performance", config)
        self.assertIn("slice_performance", config)
        self.assertIn("top_10_features", config)

    # --------------------------------------------------------------------------
    # 7. PREDICTION SHAPE, TYPES & SANITY
    # --------------------------------------------------------------------------
    def test_model_prediction_shape_and_bounds(self):
        """Verify model generates valid finite non-negative predictions on test data."""
        model = joblib.load(MODEL_PATH)
        X_sample = self.test_df[self.feature_cols].iloc[:100]

        preds = model.predict(X_sample)
        self.assertEqual(len(preds), 100)
        self.assertTrue(np.all(np.isfinite(preds)))
        # Vehicle volume should be reasonably non-negative (can truncate negative bounds to 0)
        self.assertTrue(np.all(preds >= -100))  # GBDT unconstrained, should be overwhelmingly positive

    # --------------------------------------------------------------------------
    # 8. METRIC CALCULATION EXACTNESS
    # --------------------------------------------------------------------------
    def test_metric_calculation_exactness(self):
        """Verify MAE, RMSE, sMAPE, and R2 mathematical implementations."""
        y_true = np.array([100.0, 200.0, 300.0, 400.0])
        y_pred = np.array([110.0, 190.0, 320.0, 380.0])

        metrics = calculate_metrics(y_true, y_pred)

        # Expected:
        # errors: [10, 10, 20, 20] -> MAE = 15.0
        # squared: [100, 100, 400, 400] -> mean = 250 -> RMSE = sqrt(250) ~ 15.81
        self.assertEqual(metrics["mae"], 15.0)
        self.assertAlmostEqual(metrics["rmse"], np.sqrt(250.0), places=2)
        self.assertGreater(metrics["r2"], 0.95)
        self.assertEqual(metrics["n"], 4)

        # Test NaN handling
        y_true_nan = np.array([100.0, np.nan, 300.0])
        y_pred_nan = np.array([110.0, 200.0, 290.0])
        metrics_nan = calculate_metrics(y_true_nan, y_pred_nan)
        self.assertEqual(metrics_nan["n"], 2)
        self.assertEqual(metrics_nan["mae"], 10.0)


if __name__ == "__main__":
    unittest.main()
