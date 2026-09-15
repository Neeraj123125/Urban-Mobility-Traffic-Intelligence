-- ==============================================================================
-- Urban Mobility & Traffic Intelligence - Phase 3 Analytical Views
-- Script: sql/03_analysis_views.sql
-- Description: Production Analytical Views for I-94 Traffic Data Mart
-- Dialect: ANSI SQL / SQLite (3.25+) / PostgreSQL / DuckDB compatible
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. VIEW: HOURLY TRAFFIC PROFILE
-- Diurnal 24-hour traffic volume curve
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_hourly_traffic_profile;
CREATE VIEW vw_hourly_traffic_profile AS
SELECT
    c.hour_val AS hour_of_day,
    COUNT(f.fact_id) AS observation_count,
    ROUND(AVG(f.traffic_volume), 2) AS avg_traffic_volume,
    MIN(f.traffic_volume) AS min_traffic_volume,
    MAX(f.traffic_volume) AS max_traffic_volume
FROM fact_traffic_hourly f
JOIN dim_calendar c ON f.calendar_key = c.calendar_key
GROUP BY c.hour_val
ORDER BY c.hour_val;

-- ------------------------------------------------------------------------------
-- 2. VIEW: MORNING VS. EVENING RUSH
-- Direct comparison between Morning Rush (06-09) and Evening Rush (15-18)
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_morning_vs_evening_rush;
CREATE VIEW vw_morning_vs_evening_rush AS
SELECT
    CASE
        WHEN c.is_morning_rush_hour = 1 THEN 'Morning Rush (06:00-09:00 Mon-Fri)'
        WHEN c.is_evening_rush_hour = 1 THEN 'Evening Rush (15:00-18:00 Mon-Fri)'
    END AS rush_period,
    COUNT(f.fact_id) AS hours_observed,
    ROUND(AVG(f.traffic_volume), 2) AS avg_volume,
    MIN(f.traffic_volume) AS min_volume,
    MAX(f.traffic_volume) AS max_volume,
    ROUND(AVG(f.temp_celsius), 2) AS avg_temp_celsius,
    ROUND(AVG(f.rain_1h_mm), 3) AS avg_rainfall_mm
FROM fact_traffic_hourly f
JOIN dim_calendar c ON f.calendar_key = c.calendar_key
WHERE c.is_morning_rush_hour = 1 OR c.is_evening_rush_hour = 1
GROUP BY 
    CASE
        WHEN c.is_morning_rush_hour = 1 THEN 'Morning Rush (06:00-09:00 Mon-Fri)'
        WHEN c.is_evening_rush_hour = 1 THEN 'Evening Rush (15:00-18:00 Mon-Fri)'
    END
ORDER BY avg_volume DESC;

-- Alias for commuter rush metrics
DROP VIEW IF EXISTS vw_commuter_rush_metrics;
CREATE VIEW vw_commuter_rush_metrics AS
SELECT
    CASE
        WHEN c.is_morning_rush_hour = 1 THEN 'Morning Rush (06:00-09:00 Mon-Fri)'
        WHEN c.is_evening_rush_hour = 1 THEN 'Evening Rush (15:00-18:00 Mon-Fri)'
        WHEN c.is_weekend = 0 THEN 'Weekday Off-Peak'
        ELSE 'Weekend'
    END AS operational_period,
    COUNT(f.fact_id) AS total_hours_observed,
    ROUND(AVG(f.traffic_volume), 2) AS avg_traffic_volume,
    MIN(f.traffic_volume) AS min_volume,
    MAX(f.traffic_volume) AS max_volume,
    ROUND(AVG(f.temp_celsius), 2) AS avg_temp_celsius
FROM fact_traffic_hourly f
JOIN dim_calendar c ON f.calendar_key = c.calendar_key
GROUP BY 
    CASE
        WHEN c.is_morning_rush_hour = 1 THEN 'Morning Rush (06:00-09:00 Mon-Fri)'
        WHEN c.is_evening_rush_hour = 1 THEN 'Evening Rush (15:00-18:00 Mon-Fri)'
        WHEN c.is_weekend = 0 THEN 'Weekday Off-Peak'
        ELSE 'Weekend'
    END
ORDER BY avg_traffic_volume DESC;

-- ------------------------------------------------------------------------------
-- 3. VIEW: WEEKDAY VS. WEEKEND TRAFFIC
-- High-level operational contrast between workdays and weekends
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_weekday_vs_weekend_traffic;
CREATE VIEW vw_weekday_vs_weekend_traffic AS
SELECT
    CASE WHEN c.is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS day_classification,
    COUNT(f.fact_id) AS observed_hours,
    ROUND(AVG(f.traffic_volume), 2) AS avg_volume,
    MIN(f.traffic_volume) AS min_volume,
    MAX(f.traffic_volume) AS max_volume
FROM fact_traffic_hourly f
JOIN dim_calendar c ON f.calendar_key = c.calendar_key
GROUP BY c.is_weekend
ORDER BY avg_volume DESC;

-- ------------------------------------------------------------------------------
-- 4. VIEW: DAY-OF-WEEK TRAFFIC
-- Weekly progression from Monday through Sunday
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_day_of_week_traffic;
CREATE VIEW vw_day_of_week_traffic AS
SELECT
    c.day_of_week,
    c.day_name,
    c.is_weekend,
    COUNT(f.fact_id) AS observed_hours,
    ROUND(AVG(f.traffic_volume), 2) AS avg_volume,
    MAX(f.traffic_volume) AS peak_volume,
    MIN(f.traffic_volume) AS low_volume
FROM fact_traffic_hourly f
JOIN dim_calendar c ON f.calendar_key = c.calendar_key
GROUP BY c.day_of_week, c.day_name, c.is_weekend
ORDER BY c.day_of_week;

-- ------------------------------------------------------------------------------
-- 5. VIEW: MONTHLY SEASONALITY
-- Calendar month trends and weather accumulation
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_monthly_seasonality;
CREATE VIEW vw_monthly_seasonality AS
SELECT
    c.month_val AS month_number,
    c.month_name,
    COUNT(f.fact_id) AS observed_hours,
    ROUND(AVG(f.traffic_volume), 2) AS avg_volume,
    ROUND(AVG(f.temp_celsius), 2) AS avg_temp_celsius,
    ROUND(SUM(f.rain_1h_mm), 2) AS total_rain_mm,
    ROUND(SUM(f.snow_1h_mm), 2) AS total_snow_mm
FROM fact_traffic_hourly f
JOIN dim_calendar c ON f.calendar_key = c.calendar_key
GROUP BY c.month_val, c.month_name
ORDER BY c.month_val;

-- ------------------------------------------------------------------------------
-- 6. VIEW: WEATHER IMPACT
-- Compares average traffic under each weather condition vs. Clear baseline
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_weather_impact;
CREATE VIEW vw_weather_impact AS
WITH baseline AS (
    SELECT AVG(f.traffic_volume) AS baseline_clear_vol
    FROM fact_traffic_hourly f
    JOIN dim_weather w ON f.weather_key = w.weather_key
    WHERE w.weather_main = 'Clear'
)
SELECT
    w.weather_main,
    w.hazard_level,
    COUNT(f.fact_id) AS observed_hours,
    ROUND(AVG(f.traffic_volume), 2) AS avg_volume,
    ROUND(AVG(f.rain_1h_mm), 2) AS avg_rain_mm,
    ROUND(AVG(f.snow_1h_mm), 2) AS avg_snow_mm,
    ROUND(AVG(f.temp_celsius), 2) AS avg_temp_celsius,
    ROUND(
        ((AVG(f.traffic_volume) - b.baseline_clear_vol) / b.baseline_clear_vol) * 100.0,
        2
    ) AS pct_variance_vs_clear
FROM fact_traffic_hourly f
JOIN dim_weather w ON f.weather_key = w.weather_key
CROSS JOIN baseline b
GROUP BY w.weather_main, w.hazard_level, b.baseline_clear_vol
ORDER BY avg_volume ASC;

-- ------------------------------------------------------------------------------
-- 7. VIEW: WEATHER SEVERITY IMPACT
-- Aggregates volume by standardized operational severity rank
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_weather_severity_impact;
CREATE VIEW vw_weather_severity_impact AS
SELECT
    w.severity_rank,
    w.hazard_level,
    w.weather_main,
    COUNT(f.fact_id) AS hours_count,
    ROUND(AVG(f.traffic_volume), 2) AS avg_volume,
    MIN(f.traffic_volume) AS min_volume,
    MAX(f.traffic_volume) AS max_volume
FROM fact_traffic_hourly f
JOIN dim_weather w ON f.weather_key = w.weather_key
GROUP BY w.severity_rank, w.hazard_level, w.weather_main
ORDER BY w.severity_rank DESC;

-- ------------------------------------------------------------------------------
-- 8. VIEW: TRAFFIC-VOLUME RANKINGS
-- Ranks observation days by total daily throughput
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_traffic_volume_rankings;
CREATE VIEW vw_traffic_volume_rankings AS
WITH daily_traffic AS (
    SELECT
        c.calendar_date,
        c.day_name,
        c.is_weekend,
        c.is_holiday,
        COUNT(f.fact_id) AS recorded_hours,
        SUM(f.traffic_volume) AS total_daily_volume,
        ROUND(AVG(f.traffic_volume), 2) AS avg_hourly_volume
    FROM fact_traffic_hourly f
    JOIN dim_calendar c ON f.calendar_key = c.calendar_key
    GROUP BY c.calendar_date, c.day_name, c.is_weekend, c.is_holiday
    HAVING COUNT(f.fact_id) = 24  -- Only complete 24-hour days for fair comparison
)
SELECT
    calendar_date,
    day_name,
    is_weekend,
    is_holiday,
    total_daily_volume,
    avg_hourly_volume,
    DENSE_RANK() OVER (ORDER BY total_daily_volume DESC) AS rank_highest_volume,
    DENSE_RANK() OVER (ORDER BY total_daily_volume ASC) AS rank_lowest_volume
FROM daily_traffic;

-- ------------------------------------------------------------------------------
-- 9. VIEW: PEAK TRAFFIC PERIODS
-- Extreme congestion hours exceeding 6,000 vehicles/hr
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_peak_traffic_periods;
CREATE VIEW vw_peak_traffic_periods AS
SELECT
    f.full_timestamp,
    c.day_name,
    c.hour_val,
    c.is_morning_rush_hour,
    c.is_evening_rush_hour,
    w.weather_main,
    f.traffic_volume,
    f.temp_celsius,
    f.rain_1h_mm
FROM fact_traffic_hourly f
JOIN dim_calendar c ON f.calendar_key = c.calendar_key
JOIN dim_weather w ON f.weather_key = w.weather_key
WHERE f.traffic_volume >= 6000
ORDER BY f.traffic_volume DESC;

-- ------------------------------------------------------------------------------
-- 10. VIEW: LOW TRAFFIC PERIODS
-- Trough hours with volume under 500 vehicles/hr
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_low_traffic_periods;
CREATE VIEW vw_low_traffic_periods AS
SELECT
    f.full_timestamp,
    c.day_name,
    c.hour_val,
    c.is_weekend,
    w.weather_main,
    f.traffic_volume,
    f.temp_celsius
FROM fact_traffic_hourly f
JOIN dim_calendar c ON f.calendar_key = c.calendar_key
JOIN dim_weather w ON f.weather_key = w.weather_key
WHERE f.traffic_volume <= 500
ORDER BY f.traffic_volume ASC;

-- ------------------------------------------------------------------------------
-- 11. VIEW: TRAFFIC VARIABILITY
-- Hourly volume spread and dispersion metrics across hours of day
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_traffic_variability;
CREATE VIEW vw_traffic_variability AS
SELECT
    c.hour_val,
    COUNT(f.fact_id) AS sample_size,
    ROUND(AVG(f.traffic_volume), 2) AS mean_volume,
    MIN(f.traffic_volume) AS min_volume,
    MAX(f.traffic_volume) AS max_volume,
    (MAX(f.traffic_volume) - MIN(f.traffic_volume)) AS volume_range,
    ROUND(
        CAST(MAX(f.traffic_volume) - MIN(f.traffic_volume) AS REAL) / AVG(f.traffic_volume),
        2
    ) AS relative_dispersion_ratio
FROM fact_traffic_hourly f
JOIN dim_calendar c ON f.calendar_key = c.calendar_key
GROUP BY c.hour_val
ORDER BY c.hour_val;

-- ------------------------------------------------------------------------------
-- 12. VIEW: TEMPERATURE VS. TRAFFIC
-- Binned temperature bands vs. mobility volume
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_temperature_vs_traffic;
CREATE VIEW vw_temperature_vs_traffic AS
SELECT
    CASE
        WHEN f.temp_celsius < -15 THEN '1. Severe Cold (< -15°C)'
        WHEN f.temp_celsius BETWEEN -15 AND 0 THEN '2. Freezing (-15°C to 0°C)'
        WHEN f.temp_celsius BETWEEN 0 AND 15 THEN '3. Cool (0°C to 15°C)'
        WHEN f.temp_celsius BETWEEN 15 AND 25 THEN '4. Moderate (15°C to 25°C)'
        ELSE '5. Warm / Hot (> 25°C)'
    END AS temp_band,
    COUNT(f.fact_id) AS observed_hours,
    ROUND(AVG(f.traffic_volume), 2) AS avg_volume,
    ROUND(AVG(f.temp_celsius), 2) AS avg_band_temp_celsius
FROM fact_traffic_hourly f
GROUP BY 
    CASE
        WHEN f.temp_celsius < -15 THEN '1. Severe Cold (< -15°C)'
        WHEN f.temp_celsius BETWEEN -15 AND 0 THEN '2. Freezing (-15°C to 0°C)'
        WHEN f.temp_celsius BETWEEN 0 AND 15 THEN '3. Cool (0°C to 15°C)'
        WHEN f.temp_celsius BETWEEN 15 AND 25 THEN '4. Moderate (15°C to 25°C)'
        ELSE '5. Warm / Hot (> 25°C)'
    END
ORDER BY temp_band;

-- ------------------------------------------------------------------------------
-- 13. VIEW: RAIN VS. TRAFFIC
-- Standard meteorological rainfall intensity tiers vs. highway throughput
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_rain_vs_traffic;
CREATE VIEW vw_rain_vs_traffic AS
SELECT
    CASE
        WHEN f.rain_1h_mm = 0 THEN '1. No Rain (0 mm)'
        WHEN f.rain_1h_mm < 2.5 THEN '2. Light Rain (< 2.5 mm)'
        WHEN f.rain_1h_mm <= 7.6 THEN '3. Moderate Rain (2.5 - 7.6 mm)'
        ELSE '4. Heavy Rain (> 7.6 mm)'
    END AS rainfall_tier,
    COUNT(f.fact_id) AS observed_hours,
    ROUND(AVG(f.traffic_volume), 2) AS avg_volume,
    ROUND(AVG(f.rain_1h_mm), 2) AS avg_rain_in_tier_mm
FROM fact_traffic_hourly f
GROUP BY 
    CASE
        WHEN f.rain_1h_mm = 0 THEN '1. No Rain (0 mm)'
        WHEN f.rain_1h_mm < 2.5 THEN '2. Light Rain (< 2.5 mm)'
        WHEN f.rain_1h_mm <= 7.6 THEN '3. Moderate Rain (2.5 - 7.6 mm)'
        ELSE '4. Heavy Rain (> 7.6 mm)'
    END
ORDER BY rainfall_tier;

-- ------------------------------------------------------------------------------
-- 14. VIEW: WEATHER-EVENT FREQUENCY
-- Evaluates throughput based on multi-phenomena concurrency
-- ------------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_weather_event_frequency;
CREATE VIEW vw_weather_event_frequency AS
SELECT
    f.weather_event_count AS concurrent_events_count,
    COUNT(f.fact_id) AS observed_hours,
    ROUND(AVG(f.traffic_volume), 2) AS avg_volume,
    MIN(f.traffic_volume) AS min_volume,
    MAX(f.traffic_volume) AS max_volume
FROM fact_traffic_hourly f
GROUP BY f.weather_event_count
ORDER BY f.weather_event_count ASC;
