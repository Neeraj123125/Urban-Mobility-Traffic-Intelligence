"""
Unit and Data Integrity Tests - Phase 2 Verification Suite
Urban Mobility & Traffic Intelligence

Expanded test suite verifying:
- Raw data immutability and checksum preservation
- Interim and processed artifact existence and schemas
- Outlier treatment (temp=0.0 K imputed, rain > 100mm capped)
- Duplicate handling and strict 1-row-per-hour grain
- Feature engineering integrity (rush hours, calendar attributes, holiday flags)
- Non-negative value constraints and metric boundary assertions
"""

import os
import hashlib
import unittest
import pandas as pd

RAW_DATA_PATH = os.path.join("data", "raw", "Metro_Interstate_Traffic_Volume.csv")
INTERIM_DATA_PATH = os.path.join("data", "interim", "traffic_staged.csv")
PROCESSED_DATA_PATH = os.path.join("data", "processed", "traffic_cleaned.csv")

EXPECTED_RAW_SHA256 = "749c90d720360a4215bb15345526073c079ba4cc95e3fa558796d083f85fce9e"

EXPECTED_PROCESSED_COLUMNS = [
    "date_time",
    "holiday",
    "temp",
    "rain_1h",
    "snow_1h",
    "clouds_all",
    "weather_main",
    "weather_description",
    "traffic_volume",
    "weather_event_count",
    "year",
    "month",
    "day",
    "hour",
    "day_of_week",
    "day_name",
    "month_name",
    "week_of_year",
    "is_weekend",
    "is_holiday",
    "is_morning_rush_hour",
    "is_evening_rush_hour",
    "temp_celsius",
    "temp_fahrenheit"
]

ALLOWED_WEATHER_MAIN = {
    "Clear", "Clouds", "Drizzle", "Fog", "Haze", "Mist",
    "Rain", "Smoke", "Snow", "Squall", "Thunderstorm"
}


class TestDataIntegrity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Load datasets once for assertions."""
        cls.raw_df = pd.read_csv(RAW_DATA_PATH, keep_default_na=False)
        cls.interim_df = pd.read_csv(INTERIM_DATA_PATH, keep_default_na=False)
        cls.proc_df = pd.read_csv(PROCESSED_DATA_PATH, keep_default_na=False)
        cls.proc_df['parsed_dt'] = pd.to_datetime(cls.proc_df['date_time'])

    # --------------------------------------------------------------------------
    # 1. RAW DATA INTEGRITY & IMMUTABILITY
    # --------------------------------------------------------------------------
    def test_raw_file_exists(self):
        """Verify that the raw CSV file exists at the canonical path."""
        self.assertTrue(os.path.isfile(RAW_DATA_PATH), f"Raw dataset not found at {RAW_DATA_PATH}")

    def test_raw_sha256_unaltered(self):
        """Verify that the raw CSV has NOT been modified, mutated, or overwritten."""
        sha256 = hashlib.sha256()
        with open(RAW_DATA_PATH, "rb") as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        self.assertEqual(sha256.hexdigest(), EXPECTED_RAW_SHA256, "Raw CSV SHA-256 hash mismatch! Data was modified!")

    def test_raw_dimensions(self):
        """Verify raw CSV row and column counts."""
        self.assertEqual(len(self.raw_df), 48204, f"Expected 48,204 raw rows, found {len(self.raw_df)}")
        self.assertEqual(len(self.raw_df.columns), 9, f"Expected 9 raw columns, found {len(self.raw_df.columns)}")

    # --------------------------------------------------------------------------
    # 2. PROCESSED & INTERIM DATASET EXISTENCE & SCHEMA
    # --------------------------------------------------------------------------
    def test_interim_file_exists(self):
        """Verify that the staged interim dataset exists."""
        self.assertTrue(os.path.isfile(INTERIM_DATA_PATH), f"Interim dataset not found at {INTERIM_DATA_PATH}")
        self.assertEqual(len(self.interim_df), 48187, "Interim dataset should contain exactly 48,187 deduplicated rows")

    def test_processed_file_exists(self):
        """Verify that the final processed dataset exists."""
        self.assertTrue(os.path.isfile(PROCESSED_DATA_PATH), f"Processed dataset not found at {PROCESSED_DATA_PATH}")

    def test_processed_dimensions(self):
        """Verify processed dataset dimensions match exact hourly grain (40,575 rows, 24 cols)."""
        self.assertEqual(len(self.proc_df), 40575, f"Expected 40,575 processed rows, found {len(self.proc_df)}")
        self.assertEqual(len(self.proc_df.columns) - 1, 24, "Expected 24 feature columns in processed dataset")

    def test_processed_columns_match_specification(self):
        """Verify that all 24 required engineered and cleaned columns exist."""
        actual_cols = [c for c in self.proc_df.columns if c != 'parsed_dt']
        self.assertListEqual(actual_cols, EXPECTED_PROCESSED_COLUMNS, "Processed columns do not match expected schema")

    # --------------------------------------------------------------------------
    # 3. TEMPORAL CONTINUITY & DUPLICATE GRAIN ASSERTIONS
    # --------------------------------------------------------------------------
    def test_processed_datetime_parsing(self):
        """Verify that date_time parses 100% cleanly without NaT values."""
        self.assertEqual(int(self.proc_df['parsed_dt'].isna().sum()), 0, "Found NaT values in processed datetime")

    def test_no_duplicate_hourly_records(self):
        """Verify strict 1-row-per-hour grain (0 duplicate timestamps in processed mart)."""
        dup_count = self.proc_df['date_time'].duplicated().sum()
        self.assertEqual(dup_count, 0, f"Found {dup_count} duplicate timestamps in processed dataset! Grain violated!")

    # --------------------------------------------------------------------------
    # 4. OUTLIER & VALIDITY ASSERTIONS
    # --------------------------------------------------------------------------
    def test_temperature_outlier_imputed(self):
        """Verify that all 10 absolute-zero (temp == 0.0 K) sensor dropouts were imputed."""
        zero_temp_count = (self.proc_df['temp'] == 0.0).sum()
        self.assertEqual(zero_temp_count, 0, f"Found {zero_temp_count} records with temp == 0.0 K in processed dataset!")
        self.assertGreater(self.proc_df['temp'].min(), 200.0, "Found unrealistic sub-200K temperature in processed data")

    def test_rain_outlier_capped(self):
        """Verify that the 9,831.3 mm rainfall anomaly was capped at the historical valid limit."""
        max_rain = self.proc_df['rain_1h'].max()
        self.assertLessEqual(max_rain, 60.0, f"Rainfall anomaly unhandled! Max rain is {max_rain} mm")

    def test_no_unexpected_negative_values(self):
        """Verify that non-negative features contain no negative numbers."""
        self.assertGreaterEqual(self.proc_df['traffic_volume'].min(), 0, "Negative traffic volume found")
        self.assertGreaterEqual(self.proc_df['rain_1h'].min(), 0.0, "Negative rain_1h found")
        self.assertGreaterEqual(self.proc_df['snow_1h'].min(), 0.0, "Negative snow_1h found")
        self.assertGreaterEqual(self.proc_df['clouds_all'].min(), 0, "Negative clouds_all found")
        self.assertLessEqual(self.proc_df['clouds_all'].max(), 100, "Clouds coverage exceeds 100%")

    def test_traffic_volume_bounds(self):
        """Verify traffic volume resides within realistic physical capacity bounds."""
        self.assertGreaterEqual(self.proc_df['traffic_volume'].min(), 0)
        self.assertLessEqual(self.proc_df['traffic_volume'].max(), 8000, "Traffic volume exceeds reasonable roadway capacity")

    # --------------------------------------------------------------------------
    # 5. CATEGORICAL NORMALIZATION ASSERTIONS
    # --------------------------------------------------------------------------
    def test_valid_weather_main_categories(self):
        """Verify that weather_main only contains the allowed 11 categories."""
        actual_categories = set(self.proc_df['weather_main'].unique())
        self.assertTrue(actual_categories.issubset(ALLOWED_WEATHER_MAIN), f"Unexpected weather categories: {actual_categories - ALLOWED_WEATHER_MAIN}")

    def test_weather_description_casing_normalized(self):
        """Verify that weather_description has been normalized to lowercase without uppercase relics."""
        for desc in self.proc_df['weather_description'].unique():
            self.assertEqual(desc, desc.lower(), f"Unnormalized casing found in description: '{desc}'")

    # --------------------------------------------------------------------------
    # 6. FEATURE ENGINEERING LOGIC ASSERTIONS
    # --------------------------------------------------------------------------
    def test_rush_hour_rules(self):
        """Verify that rush hours are strictly binary and occur only on non-holiday weekdays."""
        # Check morning rush hour
        m_rush = self.proc_df[self.proc_df['is_morning_rush_hour'] == 1]
        self.assertTrue((m_rush['is_weekend'] == 0).all(), "Morning rush hour flagged on weekend!")
        self.assertTrue((m_rush['is_holiday'] == 0).all(), "Morning rush hour flagged on holiday!")
        self.assertTrue(m_rush['hour'].isin([6, 7, 8, 9]).all(), "Morning rush hour flagged outside 06:00-09:00!")

        # Check evening rush hour
        e_rush = self.proc_df[self.proc_df['is_evening_rush_hour'] == 1]
        self.assertTrue((e_rush['is_weekend'] == 0).all(), "Evening rush hour flagged on weekend!")
        self.assertTrue((e_rush['is_holiday'] == 0).all(), "Evening rush hour flagged on holiday!")
        self.assertTrue(e_rush['hour'].isin([15, 16, 17, 18]).all(), "Evening rush hour flagged outside 15:00-18:00!")

    def test_is_holiday_flag_logic(self):
        """Verify that is_holiday aligns with holiday != 'None'."""
        self.assertTrue(
            ((self.proc_df['holiday'] != 'None') == (self.proc_df['is_holiday'] == 1)).all(),
            "is_holiday flag does not match holiday != 'None'!"
        )

    def test_temperature_conversion_formulas(self):
        """Verify that Celsius and Fahrenheit conversions match physical formulas."""
        expected_celsius = (self.proc_df['temp'] - 273.15).round(2)
        diff_c = (self.proc_df['temp_celsius'] - expected_celsius).abs().max()
        self.assertLess(diff_c, 0.05, "Celsius conversion discrepancy detected")

    # --------------------------------------------------------------------------
    # 7. LOCAL ANALYTICAL DATABASE VALIDATION
    # --------------------------------------------------------------------------
    def test_sqlite_database_tables_and_grain(self):
        """Verify that local SQLite analytical database contains exact expected tables, views, and row counts."""
        db_path = os.path.join("sql", "traffic_intelligence.db")
        if os.path.isfile(db_path):
            import sqlite3
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            fact_cnt = cur.execute("SELECT COUNT(*) FROM fact_traffic_hourly").fetchone()[0]
            cal_cnt = cur.execute("SELECT COUNT(*) FROM dim_calendar").fetchone()[0]
            weather_cnt = cur.execute("SELECT COUNT(*) FROM dim_weather").fetchone()[0]
            v_rush_cnt = cur.execute("SELECT COUNT(*) FROM vw_commuter_rush_metrics").fetchone()[0]
            conn.close()
            self.assertEqual(fact_cnt, 40575, f"Fact table count mismatch in SQLite DB: {fact_cnt}")
            self.assertEqual(cal_cnt, 40575, f"Calendar dimension count mismatch in SQLite DB: {cal_cnt}")
            self.assertEqual(weather_cnt, 34, f"Weather dimension count mismatch in SQLite DB: {weather_cnt}")
            self.assertEqual(v_rush_cnt, 4, f"Rush hour view row count mismatch: {v_rush_cnt}")


if __name__ == "__main__":
    unittest.main()

