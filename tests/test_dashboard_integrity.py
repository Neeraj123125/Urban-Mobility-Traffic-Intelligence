"""
Unit and Integration Tests for Phase 5: Executive Intelligence Dashboard
Urban Mobility & Traffic Intelligence

Validates:
1. Dashboard file syntax and compilation
2. Data loader parity (40,575 observed rows)
3. SQLite database integration and KPI consistency
4. Phase 4 champion model loading and config synchronization
5. Filter logic correctness (zero duplicates, zero synthetic records)
6. Metric consistency with Phase 4 report
"""

import os
import sys
import json
import sqlite3
import py_compile
import unittest
import numpy as np
import pandas as pd
import joblib

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("src"))

APP_PATH = os.path.join("dashboard", "app.py")
DB_PATH = os.path.join("sql", "traffic_intelligence.db")
PROCESSED_DATA_PATH = os.path.join("data", "processed", "traffic_cleaned.csv")
CONFIG_PATH = os.path.join("models", "feature_config.json")
MODEL_PATH = os.path.join("models", "traffic_forecaster_best.joblib")


class TestDashboardIntegrity(unittest.TestCase):
    # --------------------------------------------------------------------------
    # 1. SYNTAX & FILE INTEGRITY
    # --------------------------------------------------------------------------
    def test_dashboard_app_compilation(self):
        """Verify dashboard/app.py compiles without syntax errors."""
        self.assertTrue(os.path.isfile(APP_PATH), f"App file {APP_PATH} not found.")
        # py_compile checks for SyntaxError
        py_compile.compile(APP_PATH, doraise=True)

    # --------------------------------------------------------------------------
    # 2. DATASET INGESTION PARITY
    # --------------------------------------------------------------------------
    def test_data_ingestion_parity(self):
        """Verify processed dataset loads with exact 40,575 rows and expected columns."""
        self.assertTrue(os.path.isfile(PROCESSED_DATA_PATH))
        df = pd.read_csv(PROCESSED_DATA_PATH, parse_dates=["date_time"])
        self.assertEqual(len(df), 40575, f"Expected 40,575 rows, got {len(df)}")
        self.assertIn("traffic_volume", df.columns)
        self.assertIn("weather_main", df.columns)
        self.assertIn("is_morning_rush_hour", df.columns)
        self.assertIn("is_evening_rush_hour", df.columns)

    # --------------------------------------------------------------------------
    # 3. SQLITE DATABASE & KPI CONSISTENCY
    # --------------------------------------------------------------------------
    def test_sqlite_kpi_summary_view(self):
        """Verify SQLite database exists and vw_executive_kpi_summary returns exact baseline KPIs."""
        self.assertTrue(os.path.isfile(DB_PATH))
        with sqlite3.connect(DB_PATH) as conn:
            kpi_df = pd.read_sql_query("SELECT * FROM vw_executive_kpi_summary", conn)

        self.assertEqual(len(kpi_df), 8)
        kpi_map = dict(zip(kpi_df["kpi_metric_name"], kpi_df["kpi_metric_value"]))

        # Check key metrics match Phase 3 & 4 ground truth
        self.assertAlmostEqual(float(kpi_map["Average Hourly Traffic (Vehicles/Hr)"]), 3290.65, places=1)
        self.assertEqual(int(float(kpi_map["Peak-Hour Traffic Volume"])), 7280)
        self.assertAlmostEqual(float(kpi_map["Morning Rush Hour Average (06:00-09:00)"]), 5463.33, places=1)
        self.assertAlmostEqual(float(kpi_map["Evening Rush Hour Average (15:00-18:00)"]), 5544.75, places=1)
        self.assertAlmostEqual(float(kpi_map["Weekday Average Volume"]), 3557.44, places=1)
        self.assertAlmostEqual(float(kpi_map["Weekend Average Volume"]), 2623.93, places=1)

    # --------------------------------------------------------------------------
    # 4. MODEL ARTIFACT & CONFIGURATION SYNCHRONIZATION
    # --------------------------------------------------------------------------
    def test_model_and_config_loading(self):
        """Verify champion model artifact and metadata configuration load cleanly."""
        self.assertTrue(os.path.isfile(MODEL_PATH))
        self.assertTrue(os.path.isfile(CONFIG_PATH))

        model = joblib.load(MODEL_PATH)
        self.assertIsNotNone(model)

        with open(CONFIG_PATH, "r") as f:
            config = json.load(f)

        self.assertEqual(config["model_name"], "XGBoost")
        self.assertEqual(config["feature_count"], 39)

        # Confirm test performance matches Phase 4 report
        test_perf = {m["model"]: m for m in config["test_performance"]}
        self.assertIn("XGBoost", test_perf)
        self.assertAlmostEqual(test_perf["XGBoost"]["mae"], 130.84, places=2)
        self.assertAlmostEqual(test_perf["XGBoost"]["smape"], 5.43, places=2)
        self.assertAlmostEqual(test_perf["XGBoost"]["r2"], 0.9897, places=4)

    # --------------------------------------------------------------------------
    # 5. FILTER LOGIC INTEGRITY
    # --------------------------------------------------------------------------
    def test_filter_logic_integrity(self):
        """Verify dynamic filtering does not generate duplicate or synthetic records."""
        df = pd.read_csv(PROCESSED_DATA_PATH, parse_dates=["date_time"])

        # Test date slice
        start_date = pd.to_datetime("2018-04-01").date()
        end_date = pd.to_datetime("2018-09-30").date()
        filtered = df[(df["date_time"].dt.date >= start_date) & (df["date_time"].dt.date <= end_date)]

        self.assertEqual(len(filtered), 4386)
        self.assertEqual(filtered["date_time"].duplicated().sum(), 0)

        # Test weekday filter
        weekdays = filtered[filtered["is_weekend"] == 0]
        weekends = filtered[filtered["is_weekend"] == 1]
        self.assertEqual(len(weekdays) + len(weekends), 4386)
        self.assertEqual(len(weekdays), 3116)
        self.assertEqual(len(weekends), 1270)

    # --------------------------------------------------------------------------
    # 6. KPI CARD & HTML RENDERING INTEGRITY
    # --------------------------------------------------------------------------
    def test_kpi_card_and_html_rendering_integrity(self):
        """Verify KPI cards and all HTML markdown calls render cleanly without raw code blocks."""
        with open(APP_PATH, "r", encoding="utf-8") as f:
            app_code = f.read()

        # Check render_kpi_card function exists and uses clean st.markdown
        self.assertIn("def render_kpi_card(", app_code)
        self.assertIn("st.markdown(html_content, unsafe_allow_html=True)", app_code)

        # Confirm .kpi-top was not mistakenly added
        self.assertNotIn(".kpi-top", app_code)

        # Confirm standard KPI classes exist
        self.assertIn(".kpi-card", app_code)
        self.assertIn(".kpi-label", app_code)
        self.assertIn(".kpi-value", app_code)
        self.assertIn(".kpi-sub", app_code)

        # Confirm no st.write, st.text, st.code calls exist in dashboard/app.py
        import ast
        tree = ast.parse(app_code)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = ""
                curr = node.func
                parts = []
                while isinstance(curr, ast.Attribute):
                    parts.append(curr.attr)
                    curr = curr.value
                if isinstance(curr, ast.Name):
                    parts.append(curr.id)
                    func_name = ".".join(reversed(parts))
                self.assertNotIn(func_name, ["st.write", "st.text", "st.code"])

                # For every st.markdown call that contains HTML, verify unsafe_allow_html=True
                if "markdown" in func_name and node.args:
                    arg = node.args[0]
                    # If literal string with HTML
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        if "<div" in arg.value or "<span" in arg.value or "<h" in arg.value:
                            has_unsafe = any(kw.arg == "unsafe_allow_html" and getattr(kw.value, "value", None) is True for kw in node.keywords)
                            self.assertTrue(has_unsafe, f"HTML markdown call at line {node.lineno} missing unsafe_allow_html=True")
                            # Also check no blank line followed by 4+ spaces inside HTML
                            lines = arg.value.split("\n")
                            for i, l in enumerate(lines):
                                self.assertFalse(l.startswith("    "), f"Indented line {i} in HTML markdown at line {node.lineno} could trigger code block")


if __name__ == "__main__":
    unittest.main()
