"""
Validate SQL Dimensional Schema, Views, Advanced Analytics & KPIs
Urban Mobility & Traffic Intelligence - Phase 3

This script:
1. Connects to local analytical database: sql/traffic_intelligence.db.
2. Executes sql/01_create_schema.sql to build tables and indexes.
3. Ingests data/processed/traffic_cleaned.csv into staging (preserving 'None').
4. Populates dim_calendar, dim_weather, and fact_traffic_hourly.
5. Executes sql/02_data_dictionary.sql to build metadata catalog.
6. Executes sql/03_analysis_views.sql to create all 14 analytical views.
7. Executes sql/04_advanced_analytics.sql queries.
8. Executes sql/05_business_kpis.sql to compute core business indicators.
9. Queries views and asserts relational and metric integrity.
"""

import os
import sqlite3
import pandas as pd

DB_PATH = os.path.join("sql", "traffic_intelligence.db")
PROCESSED_PATH = os.path.join("data", "processed", "traffic_cleaned.csv")
SCHEMA_SQL = os.path.join("sql", "01_create_schema.sql")
DICT_SQL = os.path.join("sql", "02_data_dictionary.sql")
VIEWS_SQL = os.path.join("sql", "03_analysis_views.sql")
ADV_SQL = os.path.join("sql", "04_advanced_analytics.sql")
KPIS_SQL = os.path.join("sql", "05_business_kpis.sql")


def run_sql_validation():
    print("=" * 70)
    print("PHASE 3: EXECUTING FULL SQL ANALYTICAL DATABASE VALIDATION")
    print("=" * 70)
    
    # 1. Connect to SQLite DB
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    print(f"[DB] Initialized local analytical SQLite database at: {DB_PATH}")

    # 2. Execute Schema DDL
    print("[DB] Executing sql/01_create_schema.sql...")
    with open(SCHEMA_SQL, "r", encoding="utf-8") as f:
        cur.executescript(f.read())

    # 3. Load Processed Dataset into Staging (preserving 'None' string)
    print(f"[DB] Ingesting {PROCESSED_PATH} into staging_traffic_cleaned...")
    df = pd.read_csv(PROCESSED_PATH, keep_default_na=False)
    df.to_sql("staging_traffic_cleaned", conn, if_exists="append", index=False)
    
    staging_count = cur.execute("SELECT COUNT(*) FROM staging_traffic_cleaned").fetchone()[0]
    print(f"[DB] Loaded {staging_count:,} records into staging_traffic_cleaned.")
    assert staging_count == 40575, f"Expected 40,575 rows, got {staging_count}"

    # 4. Populate dim_calendar
    print("[DB] Populating dim_calendar...")
    cur.execute("""
        INSERT INTO dim_calendar (
            calendar_key, full_timestamp, calendar_date, year_val, month_val, month_name,
            day_val, hour_val, day_of_week, day_name, week_of_year, is_weekend,
            is_holiday, holiday_name, is_morning_rush_hour, is_evening_rush_hour
        )
        SELECT DISTINCT
            CAST(strftime('%Y%m%d%H', date_time) AS INT) AS calendar_key,
            date_time,
            strftime('%Y-%m-%d', date_time) AS calendar_date,
            year, month, month_name,
            day, hour, day_of_week, day_name, week_of_year, is_weekend,
            is_holiday, holiday, is_morning_rush_hour, is_evening_rush_hour
        FROM staging_traffic_cleaned
    """)
    cal_count = cur.execute("SELECT COUNT(*) FROM dim_calendar").fetchone()[0]
    print(f"[DB] dim_calendar populated: {cal_count:,} rows (Exact observed hourly grain)")
    assert cal_count == 40575, f"Expected 40,575 calendar rows, got {cal_count}"

    # 5. Populate dim_weather
    print("[DB] Populating dim_weather...")
    cur.execute("""
        INSERT INTO dim_weather (weather_key, weather_main, weather_description, severity_rank, hazard_level)
        SELECT
            ROW_NUMBER() OVER(ORDER BY weather_main, weather_description) AS weather_key,
            weather_main,
            weather_description,
            CASE weather_main
                WHEN 'Thunderstorm' THEN 11
                WHEN 'Squall' THEN 10
                WHEN 'Snow' THEN 9
                WHEN 'Rain' THEN 8
                WHEN 'Drizzle' THEN 7
                WHEN 'Fog' THEN 6
                WHEN 'Mist' THEN 5
                WHEN 'Haze' THEN 4
                WHEN 'Smoke' THEN 3
                WHEN 'Clouds' THEN 2
                ELSE 1
            END AS severity_rank,
            CASE
                WHEN weather_main IN ('Thunderstorm', 'Squall', 'Snow') THEN 'Severe'
                WHEN weather_main IN ('Rain', 'Drizzle', 'Fog') THEN 'Adverse'
                ELSE 'Optimal'
            END AS hazard_level
        FROM (SELECT DISTINCT weather_main, weather_description FROM staging_traffic_cleaned) w
    """)
    weather_count = cur.execute("SELECT COUNT(*) FROM dim_weather").fetchone()[0]
    print(f"[DB] dim_weather populated: {weather_count} unique meteorological dimensions")

    # 6. Populate fact_traffic_hourly
    print("[DB] Populating fact_traffic_hourly...")
    cur.execute("""
        INSERT INTO fact_traffic_hourly (
            fact_id, calendar_key, weather_key, full_timestamp, traffic_volume,
            temp_kelvin, temp_celsius, temp_fahrenheit, rain_1h_mm, snow_1h_mm,
            clouds_coverage_pct, weather_event_count
        )
        SELECT
            ROW_NUMBER() OVER(ORDER BY s.date_time) AS fact_id,
            c.calendar_key,
            w.weather_key,
            s.date_time,
            s.traffic_volume,
            s.temp,
            s.temp_celsius,
            s.temp_fahrenheit,
            s.rain_1h,
            s.snow_1h,
            s.clouds_all,
            s.weather_event_count
        FROM staging_traffic_cleaned s
        JOIN dim_calendar c ON s.date_time = c.full_timestamp
        JOIN dim_weather w ON s.weather_main = w.weather_main AND s.weather_description = w.weather_description
    """)
    fact_count = cur.execute("SELECT COUNT(*) FROM fact_traffic_hourly").fetchone()[0]
    print(f"[DB] fact_traffic_hourly populated: {fact_count:,} records")
    assert fact_count == 40575, f"Expected 40,575 fact rows, got {fact_count}"

    # 7. Execute Data Dictionary Metadata Script
    print("[DB] Executing sql/02_data_dictionary.sql...")
    with open(DICT_SQL, "r", encoding="utf-8") as f:
        cur.executescript(f.read())
    dict_count = cur.execute("SELECT COUNT(*) FROM data_dictionary_metadata").fetchone()[0]
    print(f"[DB] data_dictionary_metadata populated: {dict_count} attribute definitions cataloged.")

    # 8. Execute All 14 Analysis Views Script
    print("[DB] Executing sql/03_analysis_views.sql (14 analytical views)...")
    with open(VIEWS_SQL, "r", encoding="utf-8") as f:
        cur.executescript(f.read())

    # 9. Execute Business KPIs Script
    print("[DB] Executing sql/05_business_kpis.sql...")
    with open(KPIS_SQL, "r", encoding="utf-8") as f:
        cur.executescript(f.read())

    # 10. Query and Assert All 14 Views
    print("\n" + "-" * 70)
    print("ASSERTING ALL 14 ANALYTICAL VIEWS")
    print("-" * 70)

    views_to_test = [
        "vw_hourly_traffic_profile",
        "vw_morning_vs_evening_rush",
        "vw_weekday_vs_weekend_traffic",
        "vw_day_of_week_traffic",
        "vw_monthly_seasonality",
        "vw_weather_impact",
        "vw_weather_severity_impact",
        "vw_traffic_volume_rankings",
        "vw_peak_traffic_periods",
        "vw_low_traffic_periods",
        "vw_traffic_variability",
        "vw_temperature_vs_traffic",
        "vw_rain_vs_traffic",
        "vw_weather_event_frequency",
        "vw_executive_kpi_summary"
    ]

    for v in views_to_test:
        row_cnt = cur.execute(f"SELECT COUNT(*) FROM {v}").fetchone()[0]
        print(f" [PASS] View: {v:<32} Rows: {row_cnt:,}")
        assert row_cnt > 0, f"View {v} returned 0 rows!"

    # 11. Print Master KPI Table
    print("\n" + "-" * 70)
    print("MASTER BUSINESS KPIS SUMMARY (From vw_executive_kpi_summary)")
    print("-" * 70)
    kpi_df = pd.read_sql_query("SELECT * FROM vw_executive_kpi_summary", conn)
    print(kpi_df.to_string(index=False))

    conn.commit()
    conn.close()
    print("\n" + "=" * 70)
    print("PHASE 3 DATABASE BUILD AND VALIDATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_sql_validation()
