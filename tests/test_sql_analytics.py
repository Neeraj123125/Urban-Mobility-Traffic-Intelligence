"""
Unit and Integration Tests for Phase 3 SQL Analytics & Dimensional Data Mart
Urban Mobility & Traffic Intelligence

Validates:
- SQLite database connection and table existence
- Dimensional grain and row count assertions
- Foreign key referential integrity (zero orphan fact records)
- All 14 analytical views execute cleanly and return non-zero rows
- Executive KPI view integrity and mathematical logic
"""

import os
import sqlite3
import unittest
import pandas as pd

DB_PATH = os.path.join("sql", "traffic_intelligence.db")


class TestSqlAnalytics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Ensure database exists and initialize connection."""
        if not os.path.isfile(DB_PATH):
            raise FileNotFoundError(f"Database {DB_PATH} not found. Run src/validate_sql_db.py first.")
        cls.conn = sqlite3.connect(DB_PATH)
        cls.cur = cls.conn.cursor()

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    # --------------------------------------------------------------------------
    # 1. SCHEMA & TABLE ROW COUNT ASSERTIONS
    # --------------------------------------------------------------------------
    def test_database_tables_exist(self):
        """Verify that all core dimensional and staging tables exist."""
        expected_tables = {
            "staging_traffic_cleaned",
            "dim_calendar",
            "dim_weather",
            "fact_traffic_hourly",
            "data_dictionary_metadata"
        }
        self.cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        actual_tables = {row[0] for row in self.cur.fetchall()}
        self.assertTrue(expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}")

    def test_fact_and_dimension_row_counts(self):
        """Verify that fact and dimension tables match expected strict observed grain."""
        fact_count = self.cur.execute("SELECT COUNT(*) FROM fact_traffic_hourly").fetchone()[0]
        cal_count = self.cur.execute("SELECT COUNT(*) FROM dim_calendar").fetchone()[0]
        weather_count = self.cur.execute("SELECT COUNT(*) FROM dim_weather").fetchone()[0]

        self.assertEqual(fact_count, 40575, f"Expected 40,575 fact rows, got {fact_count}")
        self.assertEqual(cal_count, 40575, f"Expected 40,575 calendar rows, got {cal_count}")
        self.assertEqual(weather_count, 34, f"Expected 34 weather dimensions, got {weather_count}")

    # --------------------------------------------------------------------------
    # 2. REFERENTIAL INTEGRITY ASSERTIONS
    # --------------------------------------------------------------------------
    def test_referential_integrity_calendar_key(self):
        """Verify zero orphan fact records referencing non-existent calendar keys."""
        query = """
            SELECT COUNT(*)
            FROM fact_traffic_hourly f
            LEFT JOIN dim_calendar c ON f.calendar_key = c.calendar_key
            WHERE c.calendar_key IS NULL
        """
        orphan_count = self.cur.execute(query).fetchone()[0]
        self.assertEqual(orphan_count, 0, f"Found {orphan_count} orphan facts with invalid calendar_key!")

    def test_referential_integrity_weather_key(self):
        """Verify zero orphan fact records referencing non-existent weather keys."""
        query = """
            SELECT COUNT(*)
            FROM fact_traffic_hourly f
            LEFT JOIN dim_weather w ON f.weather_key = w.weather_key
            WHERE w.weather_key IS NULL
        """
        orphan_count = self.cur.execute(query).fetchone()[0]
        self.assertEqual(orphan_count, 0, f"Found {orphan_count} orphan facts with invalid weather_key!")

    # --------------------------------------------------------------------------
    # 3. ANALYTICAL VIEWS EXISTENCE AND RECORD VALIDATION
    # --------------------------------------------------------------------------
    def test_all_14_analytical_views_exist_and_populate(self):
        """Verify that all 14 analytical views exist and return non-empty datasets."""
        views_to_test = [
            ("vw_hourly_traffic_profile", 24),
            ("vw_morning_vs_evening_rush", 2),
            ("vw_weekday_vs_weekend_traffic", 2),
            ("vw_day_of_week_traffic", 7),
            ("vw_monthly_seasonality", 12),
            ("vw_weather_impact", 11),
            ("vw_weather_severity_impact", 11),
            ("vw_traffic_volume_rankings", 1178),
            ("vw_peak_traffic_periods", 3064),
            ("vw_low_traffic_periods", 4761),
            ("vw_traffic_variability", 24),
            ("vw_temperature_vs_traffic", 5),
            ("vw_rain_vs_traffic", 4),
            ("vw_weather_event_frequency", 6),
            ("vw_executive_kpi_summary", 8)
        ]

        for view_name, expected_min_rows in views_to_test:
            with self.subTest(view=view_name):
                row_cnt = self.cur.execute(f"SELECT COUNT(*) FROM {view_name}").fetchone()[0]
                self.assertGreaterEqual(
                    row_cnt, expected_min_rows,
                    f"View {view_name} returned {row_cnt} rows, expected at least {expected_min_rows}"
                )

    # --------------------------------------------------------------------------
    # 4. BUSINESS KPI MATHEMATICAL ASSERTIONS
    # --------------------------------------------------------------------------
    def test_business_kpi_metrics(self):
        """Verify mathematical relationships of core operational traffic KPIs."""
        # 1. Peak hour volume
        peak_vol = self.cur.execute("SELECT MAX(traffic_volume) FROM fact_traffic_hourly").fetchone()[0]
        self.assertEqual(peak_vol, 7280, f"Expected absolute peak volume of 7,280, got {peak_vol}")

        # 2. Morning rush vs Evening rush vs Weekday average
        m_rush = self.cur.execute("""
            SELECT AVG(f.traffic_volume)
            FROM fact_traffic_hourly f
            JOIN dim_calendar c ON f.calendar_key = c.calendar_key
            WHERE c.is_morning_rush_hour = 1
        """).fetchone()[0]

        e_rush = self.cur.execute("""
            SELECT AVG(f.traffic_volume)
            FROM fact_traffic_hourly f
            JOIN dim_calendar c ON f.calendar_key = c.calendar_key
            WHERE c.is_evening_rush_hour = 1
        """).fetchone()[0]

        weekday_avg = self.cur.execute("""
            SELECT AVG(f.traffic_volume)
            FROM fact_traffic_hourly f
            JOIN dim_calendar c ON f.calendar_key = c.calendar_key
            WHERE c.is_weekend = 0
        """).fetchone()[0]

        weekend_avg = self.cur.execute("""
            SELECT AVG(f.traffic_volume)
            FROM fact_traffic_hourly f
            JOIN dim_calendar c ON f.calendar_key = c.calendar_key
            WHERE c.is_weekend = 1
        """).fetchone()[0]

        self.assertGreater(e_rush, m_rush, "Evening rush average should exceed morning rush average")
        self.assertGreater(m_rush, weekday_avg, "Morning rush average should exceed overall weekday average")
        self.assertGreater(weekday_avg, weekend_avg, "Weekday average should exceed weekend average")

        # 3. Minimum traffic hour
        trough_hour = self.cur.execute("""
            SELECT hour_of_day, avg_traffic_volume
            FROM vw_hourly_traffic_profile
            ORDER BY avg_traffic_volume ASC
            LIMIT 1
        """).fetchone()
        self.assertEqual(trough_hour[0], 3, f"Expected 03:00 to be lowest traffic hour, got {trough_hour[0]}")
        self.assertAlmostEqual(trough_hour[1], 373.21, places=1)


if __name__ == "__main__":
    unittest.main()
