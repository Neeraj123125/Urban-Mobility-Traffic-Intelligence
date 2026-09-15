-- ==============================================================================
-- Urban Mobility & Traffic Intelligence - Phase 2 SQL Preparation
-- Script: sql/02_data_dictionary.sql
-- Description: SQL Metadata, Table Comments & System Data Catalog
-- Dialect: ANSI SQL / SQLite / PostgreSQL / DuckDB compatible
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. SYSTEM METADATA CATALOG TABLE (Universal / SQLite / ANSI compatible)
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS data_dictionary_metadata;

CREATE TABLE data_dictionary_metadata (
    entity_name              TEXT NOT NULL,
    attribute_name           TEXT NOT NULL,
    data_type                TEXT NOT NULL,
    role                     TEXT NOT NULL,
    description              TEXT NOT NULL
);

-- Populate Data Dictionary Catalog
INSERT INTO data_dictionary_metadata VALUES
('dim_calendar', 'calendar_key', 'INTEGER', 'Primary Key', 'Smart integer key formatted as YYYYMMDDHH (e.g., 2012100209).'),
('dim_calendar', 'full_timestamp', 'TEXT / TIMESTAMP', 'Unique Natural Key', 'Exact hourly observation timestamp in ISO-8601 format (YYYY-MM-DD HH:MM:SS).'),
('dim_calendar', 'calendar_date', 'TEXT / DATE', 'Dimension Attribute', 'Observation date component (YYYY-MM-DD).'),
('dim_calendar', 'year_val', 'INTEGER', 'Dimension Attribute', 'Calendar year of observation (2012 through 2018).'),
('dim_calendar', 'month_val', 'INTEGER', 'Dimension Attribute', 'Calendar month integer (1 to 12).'),
('dim_calendar', 'month_name', 'TEXT', 'Dimension Attribute', 'Full month name (January through December).'),
('dim_calendar', 'day_val', 'INTEGER', 'Dimension Attribute', 'Day of month (1 to 31).'),
('dim_calendar', 'hour_val', 'INTEGER', 'Dimension Attribute', 'Hour of day in 24-hour military time (0 to 23).'),
('dim_calendar', 'day_of_week', 'INTEGER', 'Dimension Attribute', 'Day of week index where 0 = Monday and 6 = Sunday.'),
('dim_calendar', 'day_name', 'TEXT', 'Dimension Attribute', 'Full name of the day of the week (Monday through Sunday).'),
('dim_calendar', 'week_of_year', 'INTEGER', 'Dimension Attribute', 'ISO 8601 calendar week number (1 to 53).'),
('dim_calendar', 'is_weekend', 'INTEGER', 'Binary Flag', 'Binary flag: 1 if day is Saturday or Sunday, 0 if Monday through Friday.'),
('dim_calendar', 'is_holiday', 'INTEGER', 'Binary Flag', 'Binary flag: 1 if observation coincides with an official holiday, 0 for normal days.'),
('dim_calendar', 'holiday_name', 'TEXT', 'Dimension Attribute', 'Official holiday label or string literal None for regular baseline operations.'),
('dim_calendar', 'is_morning_rush_hour', 'INTEGER', 'Binary Flag', 'Binary flag: 1 if non-holiday weekday and hour is 06, 07, 08, or 09; else 0.'),
('dim_calendar', 'is_evening_rush_hour', 'INTEGER', 'Binary Flag', 'Binary flag: 1 if non-holiday weekday and hour is 15, 16, 17, or 18; else 0.'),

('dim_weather', 'weather_key', 'INTEGER', 'Primary Key', 'Surrogate integer primary key for meteorological condition.'),
('dim_weather', 'weather_main', 'TEXT', 'Dimension Attribute', 'High-level macro weather classification (Clear, Clouds, Rain, Snow, Thunderstorm, etc.).'),
('dim_weather', 'weather_description', 'TEXT', 'Dimension Attribute', 'Normalized lowercase detailed atmospheric condition description.'),
('dim_weather', 'severity_rank', 'INTEGER', 'Analytical Hierarchy', 'Integer rank from 1 (Clear) to 11 (Thunderstorm) governing weather dominance.'),
('dim_weather', 'hazard_level', 'TEXT', 'Categorical Classification', 'Operational driving hazard rating: Optimal, Adverse, or Severe.'),

('fact_traffic_hourly', 'fact_id', 'INTEGER', 'Primary Key', 'Unique surrogate identity key for each hourly traffic observation.'),
('fact_traffic_hourly', 'calendar_key', 'INTEGER', 'Foreign Key', 'References dim_calendar.calendar_key.'),
('fact_traffic_hourly', 'weather_key', 'INTEGER', 'Foreign Key', 'References dim_weather.weather_key.'),
('fact_traffic_hourly', 'full_timestamp', 'TEXT / TIMESTAMP', 'Unique Attribute', 'Chronological timestamp of observation (strict 1-to-1 hourly grain).'),
('fact_traffic_hourly', 'traffic_volume', 'INTEGER', 'Primary Target KPI', 'Total westbound vehicular volume count recorded by I-94 ATR Station 301.'),
('fact_traffic_hourly', 'temp_kelvin', 'REAL', 'Continuous Measure', 'Hourly average ambient temperature in Kelvin (linear interpolation for 10 zero-dropouts).'),
('fact_traffic_hourly', 'temp_celsius', 'REAL', 'Derived Measure', 'Ambient temperature converted to Celsius (K - 273.15).'),
('fact_traffic_hourly', 'temp_fahrenheit', 'REAL', 'Derived Measure', 'Ambient temperature converted to Fahrenheit ((K - 273.15)*9/5 + 32).'),
('fact_traffic_hourly', 'rain_1h_mm', 'REAL', 'Continuous Measure', 'Hourly liquid precipitation in mm (capped at historical maximum 55.63 mm).'),
('fact_traffic_hourly', 'snow_1h_mm', 'REAL', 'Continuous Measure', 'Hourly snowfall accumulation in millimeters.'),
('fact_traffic_hourly', 'clouds_coverage_pct', 'INTEGER', 'Discrete Measure', 'Cloud coverage percentage across the celestial dome (0 to 100%).'),
('fact_traffic_hourly', 'weather_event_count', 'INTEGER', 'Audit Measure', 'Count of raw meteorological events concurrently logged by weather station during the hour.');

-- ------------------------------------------------------------------------------
-- 2. POSTGRESQL NATIVE METADATA COMMENTS (Executed on PostgreSQL engines)
-- ------------------------------------------------------------------------------
/*
COMMENT ON TABLE dim_calendar IS 'Calendar dimension capturing hourly resolution, calendar attributes, holidays, and commuter rush-hour flags for I-94 traffic analysis.';
COMMENT ON TABLE dim_weather IS 'Meteorological dimension cataloging macro weather classifications, granular descriptions, and operational severity hazard rankings.';
COMMENT ON TABLE fact_traffic_hourly IS 'Central fact table containing hourly westbound I-94 vehicular counts, ambient temperature measurements, precipitation, and cloud cover.';
*/
