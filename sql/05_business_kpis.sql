-- ==============================================================================
-- Urban Mobility & Traffic Intelligence - Phase 3 Business-Oriented KPIs
-- Script: sql/05_business_kpis.sql
-- Description: Core Operational Performance Indicators for Highway Management
-- Dialect: ANSI SQL / SQLite / PostgreSQL / DuckDB compatible
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. MASTER EXECUTIVE KPI SUMMARY TABLE / QUERY
-- Aggregates the 10 core operational transportation benchmarks into a single view
-- ------------------------------------------------------------------------------
WITH 
global_kpis AS (
    SELECT
        COUNT(fact_id) AS total_hours_observed,
        ROUND(AVG(traffic_volume), 2) AS average_hourly_traffic,
        MAX(traffic_volume) AS absolute_peak_hour_volume,
        MIN(traffic_volume) AS absolute_min_hour_volume
    FROM fact_traffic_hourly
),
rush_kpis AS (
    SELECT
        ROUND(AVG(CASE WHEN c.is_morning_rush_hour = 1 THEN f.traffic_volume END), 2) AS morning_rush_average,
        ROUND(AVG(CASE WHEN c.is_evening_rush_hour = 1 THEN f.traffic_volume END), 2) AS evening_rush_average,
        ROUND(AVG(CASE WHEN c.is_weekend = 0 THEN f.traffic_volume END), 2) AS weekday_average,
        ROUND(AVG(CASE WHEN c.is_weekend = 1 THEN f.traffic_volume END), 2) AS weekend_average
    FROM fact_traffic_hourly f
    JOIN dim_calendar c ON f.calendar_key = c.calendar_key
),
weather_kpis AS (
    SELECT
        ROUND(AVG(CASE WHEN w.weather_main = 'Clear' THEN f.traffic_volume END), 2) AS clear_weather_baseline_traffic,
        ROUND(AVG(CASE WHEN w.hazard_level = 'Severe' THEN f.traffic_volume END), 2) AS severe_weather_average_traffic,
        ROUND(
            (AVG(CASE WHEN w.hazard_level = 'Severe' THEN f.traffic_volume END) - 
             AVG(CASE WHEN w.weather_main = 'Clear' THEN f.traffic_volume END)) / 
             AVG(CASE WHEN w.weather_main = 'Clear' THEN f.traffic_volume END) * 100.0,
            2
        ) AS severe_weather_throughput_penalty_pct
    FROM fact_traffic_hourly f
    JOIN dim_weather w ON f.weather_key = w.weather_key
),
day_ranking AS (
    SELECT
        c.calendar_date,
        c.day_name,
        SUM(f.traffic_volume) AS total_daily_volume
    FROM fact_traffic_hourly f
    JOIN dim_calendar c ON f.calendar_key = c.calendar_key
    GROUP BY c.calendar_date, c.day_name
    HAVING COUNT(f.fact_id) = 24  -- Strict full 24-hour days
),
extreme_days AS (
    SELECT
        (SELECT calendar_date || ' (' || day_name || '): ' || total_daily_volume || ' vehicles'
         FROM day_ranking ORDER BY total_daily_volume DESC LIMIT 1) AS highest_traffic_day,
        (SELECT calendar_date || ' (' || day_name || '): ' || total_daily_volume || ' vehicles'
         FROM day_ranking ORDER BY total_daily_volume ASC LIMIT 1) AS lowest_traffic_day
)
SELECT
    g.total_hours_observed,
    g.average_hourly_traffic,
    g.absolute_peak_hour_volume,
    r.morning_rush_average,
    r.evening_rush_average,
    r.weekday_average,
    r.weekend_average,
    w.clear_weather_baseline_traffic,
    w.severe_weather_average_traffic,
    w.severe_weather_throughput_penalty_pct,
    e.highest_traffic_day,
    e.lowest_traffic_day
FROM global_kpis g
CROSS JOIN rush_kpis r
CROSS JOIN weather_kpis w
CROSS JOIN extreme_days e;

-- ------------------------------------------------------------------------------
-- 2. DEDICATED KPI REPORTING VIEW: vw_executive_kpi_summary
-- Permanent view in the data mart for dashboard and BI ingestion
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_executive_kpi_summary;

CREATE VIEW vw_executive_kpi_summary AS
SELECT
    'Average Hourly Traffic (Vehicles/Hr)' AS kpi_metric_name,
    CAST(ROUND(AVG(traffic_volume), 2) AS TEXT) AS kpi_metric_value,
    'Baseline mean volume across all 40,575 observed hours' AS kpi_context
FROM fact_traffic_hourly
UNION ALL
SELECT
    'Peak-Hour Traffic Volume',
    CAST(MAX(traffic_volume) AS TEXT),
    'Maximum observed single-hour volume along westbound I-94'
FROM fact_traffic_hourly
UNION ALL
SELECT
    'Morning Rush Hour Average (06:00-09:00)',
    CAST(ROUND(AVG(traffic_volume), 2) AS TEXT),
    'Non-holiday Monday through Friday commuter surge'
FROM fact_traffic_hourly f
JOIN dim_calendar c ON f.calendar_key = c.calendar_key
WHERE c.is_morning_rush_hour = 1
UNION ALL
SELECT
    'Evening Rush Hour Average (15:00-18:00)',
    CAST(ROUND(AVG(traffic_volume), 2) AS TEXT),
    'Non-holiday Monday through Friday commuter crest'
FROM fact_traffic_hourly f
JOIN dim_calendar c ON f.calendar_key = c.calendar_key
WHERE c.is_evening_rush_hour = 1
UNION ALL
SELECT
    'Weekday Average Volume',
    CAST(ROUND(AVG(traffic_volume), 2) AS TEXT),
    'Monday through Friday regular operations'
FROM fact_traffic_hourly f
JOIN dim_calendar c ON f.calendar_key = c.calendar_key
WHERE c.is_weekend = 0
UNION ALL
SELECT
    'Weekend Average Volume',
    CAST(ROUND(AVG(traffic_volume), 2) AS TEXT),
    'Saturday and Sunday leisure mobility'
FROM fact_traffic_hourly f
JOIN dim_calendar c ON f.calendar_key = c.calendar_key
WHERE c.is_weekend = 1
UNION ALL
SELECT
    'Weather-Adjusted Baseline (Clear Sky)',
    CAST(ROUND(AVG(traffic_volume), 2) AS TEXT),
    'Throughput under optimal meteorological conditions'
FROM fact_traffic_hourly f
JOIN dim_weather w ON f.weather_key = w.weather_key
WHERE w.weather_main = 'Clear'
UNION ALL
SELECT
    'Severe Weather Volume (Thunderstorm/Snow/Squall)',
    CAST(ROUND(AVG(traffic_volume), 2) AS TEXT),
    'Throughput during severe hazard conditions'
FROM fact_traffic_hourly f
JOIN dim_weather w ON f.weather_key = w.weather_key
WHERE w.hazard_level = 'Severe';
