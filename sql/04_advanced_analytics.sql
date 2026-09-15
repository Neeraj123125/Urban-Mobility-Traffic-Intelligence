-- ==============================================================================
-- Urban Mobility & Traffic Intelligence - Phase 3 Advanced SQL Analytics
-- Script: sql/04_advanced_analytics.sql
-- Description: Advanced Window Functions, CTEs, Rolling Stats, and Time Comparisons
-- Dialect: ANSI SQL / SQLite (3.25+) / PostgreSQL / DuckDB compatible
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- ANALYSIS 1: HOUR-OVER-HOUR TRAFFIC ACCELERATION & SURGE
-- Demonstrates: CTE, LAG() window function, timestamp validation, percentage change
-- Identifies the fastest acceleration intervals (morning rush build-up)
-- ------------------------------------------------------------------------------
WITH hourly_lag AS (
    SELECT
        f.full_timestamp,
        c.day_name,
        c.hour_val,
        c.is_weekend,
        f.traffic_volume,
        LAG(f.full_timestamp, 1) OVER (ORDER BY f.full_timestamp) AS prev_timestamp,
        LAG(f.traffic_volume, 1) OVER (ORDER BY f.full_timestamp) AS prev_volume
    FROM fact_traffic_hourly f
    JOIN dim_calendar c ON f.calendar_key = c.calendar_key
),
hourly_deltas AS (
    SELECT
        full_timestamp,
        day_name,
        hour_val,
        is_weekend,
        traffic_volume,
        prev_volume,
        (traffic_volume - prev_volume) AS volume_change,
        ROUND(
            CAST(traffic_volume - prev_volume AS REAL) / NULLIF(prev_volume, 0) * 100.0,
            2
        ) AS pct_volume_change
    FROM hourly_lag
    WHERE prev_volume IS NOT NULL
)
SELECT
    full_timestamp,
    day_name,
    hour_val AS current_hour,
    prev_volume,
    traffic_volume AS current_volume,
    volume_change,
    pct_volume_change
FROM hourly_deltas
WHERE is_weekend = 0 AND hour_val IN (5, 6, 7)
ORDER BY volume_change DESC
LIMIT 10;

-- ------------------------------------------------------------------------------
-- ANALYSIS 2: 24-HOUR AND 7-DAY (168-HOUR) TRAILING ROLLING MOVING AVERAGES
-- Demonstrates: Window frames (ROWS BETWEEN N PRECEDING AND CURRENT ROW), smoothing
-- Filters out diurnal high-frequency noise to reveal underlying capacity trends
-- ------------------------------------------------------------------------------
SELECT
    f.full_timestamp,
    c.calendar_date,
    c.hour_val,
    f.traffic_volume,
    ROUND(
        AVG(f.traffic_volume) OVER (
            ORDER BY f.full_timestamp
            ROWS BETWEEN 23 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_24h_avg_volume,
    ROUND(
        AVG(f.traffic_volume) OVER (
            ORDER BY f.full_timestamp
            ROWS BETWEEN 167 PRECEDING AND CURRENT ROW
        ),
        2
    ) AS rolling_7d_avg_volume
FROM fact_traffic_hourly f
JOIN dim_calendar c ON f.calendar_key = c.calendar_key
ORDER BY f.full_timestamp DESC
LIMIT 20;

-- ------------------------------------------------------------------------------
-- ANALYSIS 3: DAY-OVER-DAY SAME-HOUR TRAFFIC COMPARISON
-- Demonstrates: LAG(..., 24) window function, variance attribution
-- Compares each hour against the exact same hour 24 hours prior
-- ------------------------------------------------------------------------------
WITH dod_comparison AS (
    SELECT
        f.full_timestamp,
        c.day_name,
        c.hour_val,
        c.is_weekend,
        w.weather_main,
        f.traffic_volume,
        LAG(f.traffic_volume, 24) OVER (ORDER BY f.full_timestamp) AS same_hour_yesterday_volume,
        LAG(w.weather_main, 24) OVER (ORDER BY f.full_timestamp) AS yesterday_weather
    FROM fact_traffic_hourly f
    JOIN dim_calendar c ON f.calendar_key = c.calendar_key
    JOIN dim_weather w ON f.weather_key = w.weather_key
)
SELECT
    full_timestamp,
    day_name,
    hour_val,
    weather_main AS today_weather,
    yesterday_weather,
    traffic_volume AS today_volume,
    same_hour_yesterday_volume,
    (traffic_volume - same_hour_yesterday_volume) AS dod_volume_delta,
    ROUND(
        CAST(traffic_volume - same_hour_yesterday_volume AS REAL) / NULLIF(same_hour_yesterday_volume, 0) * 100.0,
        2
    ) AS dod_pct_change
FROM dod_comparison
WHERE same_hour_yesterday_volume IS NOT NULL
  AND is_weekend = 0
  AND hour_val IN (8, 17)  -- Core rush hours
ORDER BY ABS(traffic_volume - same_hour_yesterday_volume) DESC
LIMIT 15;

-- ------------------------------------------------------------------------------
-- ANALYSIS 4: ANNUAL TOP 3 PEAK CONGESTION HOURS PER YEAR
-- Demonstrates: ROW_NUMBER(), DENSE_RANK(), PARTITION BY year
-- Identifies the highest recorded volume events in each calendar year
-- ------------------------------------------------------------------------------
WITH ranked_annual_hours AS (
    SELECT
        c.year_val,
        f.full_timestamp,
        c.day_name,
        c.month_name,
        c.hour_val,
        w.weather_main,
        f.traffic_volume,
        f.temp_celsius,
        ROW_NUMBER() OVER (
            PARTITION BY c.year_val
            ORDER BY f.traffic_volume DESC
        ) AS rank_in_year
    FROM fact_traffic_hourly f
    JOIN dim_calendar c ON f.calendar_key = c.calendar_key
    JOIN dim_weather w ON f.weather_key = w.weather_key
)
SELECT
    year_val,
    rank_in_year,
    full_timestamp,
    day_name,
    month_name,
    hour_val,
    weather_main,
    traffic_volume,
    temp_celsius
FROM ranked_annual_hours
WHERE rank_in_year <= 3
ORDER BY year_val ASC, rank_in_year ASC;

-- ------------------------------------------------------------------------------
-- ANALYSIS 5: ADVERSE WEATHER IMPACT ON COMMUTER RUSH HOURS
-- Demonstrates: Multi-CTE aggregation, conditional filtering, impact percentages
-- Measures throughput loss during morning and evening rush when weather is severe
-- ------------------------------------------------------------------------------
WITH rush_weather AS (
    SELECT
        CASE
            WHEN c.is_morning_rush_hour = 1 THEN 'Morning Rush'
            WHEN c.is_evening_rush_hour = 1 THEN 'Evening Rush'
        END AS rush_type,
        CASE
            WHEN w.hazard_level IN ('Severe', 'Adverse') THEN 'Adverse Weather (Rain/Snow/Fog)'
            ELSE 'Clear / Mild Weather'
        END AS weather_condition_type,
        f.traffic_volume
    FROM fact_traffic_hourly f
    JOIN dim_calendar c ON f.calendar_key = c.calendar_key
    JOIN dim_weather w ON f.weather_key = w.weather_key
    WHERE c.is_morning_rush_hour = 1 OR c.is_evening_rush_hour = 1
),
rush_summary AS (
    SELECT
        rush_type,
        weather_condition_type,
        COUNT(*) AS hours_count,
        ROUND(AVG(traffic_volume), 2) AS avg_volume
    FROM rush_weather
    GROUP BY rush_type, weather_condition_type
)
SELECT
    a.rush_type,
    a.avg_volume AS adverse_weather_avg_volume,
    c.avg_volume AS clear_weather_avg_volume,
    ROUND(a.avg_volume - c.avg_volume, 2) AS volume_reduction,
    ROUND(((a.avg_volume - c.avg_volume) / c.avg_volume) * 100.0, 2) AS pct_throughput_drop
FROM rush_summary a
JOIN rush_summary c ON a.rush_type = c.rush_type
WHERE a.weather_condition_type = 'Adverse Weather (Rain/Snow/Fog)'
  AND c.weather_condition_type = 'Clear / Mild Weather';

-- ------------------------------------------------------------------------------
-- ANALYSIS 6: DAILY TRAFFIC VOLATILITY INDEX & VOLUME DISPERSION
-- Demonstrates: Aggregations, daily min/max/range, and volatility ranking
-- Ranks calendar days exhibiting the highest intra-day traffic variance
-- ------------------------------------------------------------------------------
WITH daily_spreads AS (
    SELECT
        c.calendar_date,
        c.day_name,
        c.is_weekend,
        COUNT(f.fact_id) AS hours_count,
        ROUND(AVG(f.traffic_volume), 2) AS daily_avg_volume,
        MIN(f.traffic_volume) AS daily_min_volume,
        MAX(f.traffic_volume) AS daily_max_volume,
        (MAX(f.traffic_volume) - MIN(f.traffic_volume)) AS daily_volume_swing
    FROM fact_traffic_hourly f
    JOIN dim_calendar c ON f.calendar_key = c.calendar_key
    GROUP BY c.calendar_date, c.day_name, c.is_weekend
    HAVING COUNT(f.fact_id) = 24  -- Strict full 24-hour days
)
SELECT
    calendar_date,
    day_name,
    CASE WHEN is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS day_type,
    daily_avg_volume,
    daily_min_volume,
    daily_max_volume,
    daily_volume_swing,
    DENSE_RANK() OVER (ORDER BY daily_volume_swing DESC) AS volatility_rank
FROM daily_spreads
ORDER BY daily_volume_swing DESC
LIMIT 10;
