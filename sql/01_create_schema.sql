-- ==============================================================================
-- Urban Mobility & Traffic Intelligence - Phase 2 SQL Preparation
-- Script: sql/01_create_schema.sql
-- Description: Dimensional Star Schema DDL for I-94 Urban Traffic Mart
-- Dialect: ANSI SQL / SQLite / PostgreSQL / DuckDB compatible
-- Dataset Grain: Exactly ONE row per OBSERVED hourly timestamp (40,575 records)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. DROP EXISTING OBJECTS (FOR REPRODUCIBLE BUILDS)
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_hourly_traffic_summary;
DROP VIEW IF EXISTS vw_weather_impact_summary;
DROP VIEW IF EXISTS vw_commuter_rush_metrics;
DROP VIEW IF EXISTS vw_day_of_week_profile;
DROP VIEW IF EXISTS vw_monthly_seasonality;
DROP TABLE IF EXISTS fact_traffic_hourly;
DROP TABLE IF EXISTS dim_weather;
DROP TABLE IF EXISTS dim_calendar;
DROP TABLE IF EXISTS staging_traffic_cleaned;

-- ------------------------------------------------------------------------------
-- 2. STAGING TABLE: staging_traffic_cleaned
-- Matches exact schema of data/processed/traffic_cleaned.csv
-- ------------------------------------------------------------------------------
CREATE TABLE staging_traffic_cleaned (
    date_time                TEXT NOT NULL,
    holiday                  TEXT NOT NULL,
    temp                     REAL NOT NULL,
    rain_1h                  REAL NOT NULL,
    snow_1h                  REAL NOT NULL,
    clouds_all               INTEGER NOT NULL,
    weather_main             TEXT NOT NULL,
    weather_description      TEXT NOT NULL,
    traffic_volume           INTEGER NOT NULL,
    weather_event_count      INTEGER NOT NULL,
    year                     INTEGER NOT NULL,
    month                    INTEGER NOT NULL,
    day                      INTEGER NOT NULL,
    hour                     INTEGER NOT NULL,
    day_of_week              INTEGER NOT NULL,
    day_name                 TEXT NOT NULL,
    month_name               TEXT NOT NULL,
    week_of_year             INTEGER NOT NULL,
    is_weekend               INTEGER NOT NULL,
    is_holiday               INTEGER NOT NULL,
    is_morning_rush_hour     INTEGER NOT NULL,
    is_evening_rush_hour     INTEGER NOT NULL,
    temp_celsius             REAL NOT NULL,
    temp_fahrenheit          REAL NOT NULL
);

-- ------------------------------------------------------------------------------
-- 3. DIMENSION: CALENDAR & TIME (dim_calendar)
-- Grain: Exactly one row per observed hourly timestamp (40,575 records)
-- Notice: Missing historical calendar hours are NOT synthetically imputed.
-- ------------------------------------------------------------------------------
CREATE TABLE dim_calendar (
    calendar_key             INTEGER PRIMARY KEY,           -- Smart key: YYYYMMDDHH
    full_timestamp           TEXT NOT NULL UNIQUE,          -- ISO timestamp string
    calendar_date            TEXT NOT NULL,                 -- YYYY-MM-DD
    year_val                 INTEGER NOT NULL,              -- 2012 to 2018
    month_val                INTEGER NOT NULL,              -- 1 to 12
    month_name               TEXT NOT NULL,                 -- 'October'
    day_val                  INTEGER NOT NULL,              -- 1 to 31
    hour_val                 INTEGER NOT NULL,              -- 0 to 23
    day_of_week              INTEGER NOT NULL,              -- 0 = Monday, 6 = Sunday
    day_name                 TEXT NOT NULL,                 -- 'Tuesday'
    week_of_year             INTEGER NOT NULL,              -- 1 to 53
    is_weekend               INTEGER NOT NULL,              -- 1 = Sat/Sun, 0 = Mon-Fri
    is_holiday               INTEGER NOT NULL,              -- 1 = Official holiday, 0 = Normal
    holiday_name             TEXT NOT NULL,                 -- Holiday title or 'None'
    is_morning_rush_hour     INTEGER NOT NULL,              -- 1 = 06:00-09:00 Mon-Fri non-holiday
    is_evening_rush_hour     INTEGER NOT NULL               -- 1 = 15:00-18:00 Mon-Fri non-holiday
);

CREATE INDEX IF NOT EXISTS idx_dim_calendar_date ON dim_calendar(calendar_date);
CREATE INDEX IF NOT EXISTS idx_dim_calendar_hour ON dim_calendar(hour_val);
CREATE INDEX IF NOT EXISTS idx_dim_calendar_dow ON dim_calendar(day_of_week);
CREATE INDEX IF NOT EXISTS idx_dim_calendar_rush ON dim_calendar(is_morning_rush_hour, is_evening_rush_hour);

-- ------------------------------------------------------------------------------
-- 4. DIMENSION: WEATHER CONDITIONS (dim_weather)
-- Grain: Distinct combinations of macro condition and normalized description
-- ------------------------------------------------------------------------------
CREATE TABLE dim_weather (
    weather_key              INTEGER PRIMARY KEY,           -- Surrogate primary key
    weather_main             TEXT NOT NULL,                 -- Macro category (Clear, Rain, Snow, etc.)
    weather_description      TEXT NOT NULL,                 -- Lowercase normalized description
    severity_rank            INTEGER NOT NULL,              -- Priority rank (1=Clear to 11=Thunderstorm)
    hazard_level             TEXT NOT NULL                  -- 'Optimal', 'Adverse', 'Severe'
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_weather_desc ON dim_weather(weather_main, weather_description);

-- ------------------------------------------------------------------------------
-- 5. FACT TABLE: HOURLY TRAFFIC OBSERVATIONS (fact_traffic_hourly)
-- Grain: Exactly one row per observed hourly timestamp (40,575 records)
-- ------------------------------------------------------------------------------
CREATE TABLE fact_traffic_hourly (
    fact_id                  INTEGER PRIMARY KEY,           -- Surrogate identity key
    calendar_key             INTEGER NOT NULL,              -- FK to dim_calendar
    weather_key              INTEGER NOT NULL,              -- FK to dim_weather
    full_timestamp           TEXT NOT NULL UNIQUE,          -- ISO timestamp string
    traffic_volume           INTEGER NOT NULL,              -- Primary Target KPI
    temp_kelvin              REAL NOT NULL,                 -- Ambient temperature (Kelvin)
    temp_celsius             REAL NOT NULL,                 -- Ambient temperature (Celsius)
    temp_fahrenheit          REAL NOT NULL,                 -- Ambient temperature (Fahrenheit)
    rain_1h_mm               REAL NOT NULL,                 -- Hourly rainfall (capped at 55.63 mm)
    snow_1h_mm               REAL NOT NULL,                 -- Hourly snowfall (mm)
    clouds_coverage_pct      INTEGER NOT NULL,              -- Cloud cover percentage (0-100%)
    weather_event_count      INTEGER NOT NULL,              -- Weather observations logged in hour
    
    FOREIGN KEY (calendar_key) REFERENCES dim_calendar(calendar_key),
    FOREIGN KEY (weather_key) REFERENCES dim_weather(weather_key)
);

CREATE INDEX IF NOT EXISTS idx_fact_traffic_timestamp ON fact_traffic_hourly(full_timestamp);
CREATE INDEX IF NOT EXISTS idx_fact_traffic_volume ON fact_traffic_hourly(traffic_volume);
CREATE INDEX IF NOT EXISTS idx_fact_traffic_weather ON fact_traffic_hourly(weather_key);
CREATE INDEX IF NOT EXISTS idx_fact_traffic_calendar ON fact_traffic_hourly(calendar_key);
