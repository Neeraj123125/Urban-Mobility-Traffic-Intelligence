# Data Quality & Integrity Audit Report
## Urban Mobility & Traffic Intelligence — Phase 1 Foundation

**Document Version:** 1.0.0  
**Audit Date:** September 15, 2026  
**Auditor Role:** Senior Data Engineer & Data Analytics Architect  
**Dataset Reference:** `data/raw/Metro_Interstate_Traffic_Volume.csv`  
**Dataset Integrity SHA-256:** `749c90d720360a4215bb15345526073c079ba4cc95e3fa558796d083f85fce9e`  

---

## 1. Executive Summary & Dataset Overview

This data quality audit provides a forensic evaluation of the **Metro Interstate Traffic Volume** dataset, establishing the single source of truth for the *Urban Mobility & Traffic Intelligence* platform. The dataset captures hourly westbound traffic volume for Interstate 94 (I-94) connecting Minneapolis and St. Paul, Minnesota, collocated with hourly meteorological observations and holiday indicators.

The raw dataset contains **48,204 records** across **9 features** spanning October 2, 2012 through September 30, 2018 (approximately 6 years). The target variable `traffic_volume` demonstrates high structural validity with clear diurnal traffic cycles and predictable commuter patterns. However, the audit identified critical physical outliers (e.g., temperatures of 0 Kelvin, rain accumulation exceeding 9,800 mm/h), exact record duplicates, concurrent weather records for identical timestamps, and a significant 307-day historical observation blackout between August 2014 and June 2015.

---

## 2. File Information & Storage Architecture

| Property | Value / Specification |
| :--- | :--- |
| **Canonical File Path** | `data/raw/Metro_Interstate_Traffic_Volume.csv` |
| **File Size** | 3,237,208 bytes (~3.09 MB) |
| **Storage Tier** | Raw Tier (Immutable, Single Source of Truth) |
| **File Format** | Comma-Separated Values (CSV), UTF-8 text encoding |
| **Row Delimiter** | Standard CRLF / LF newline |
| **Field Delimiter** | Comma (`,`) |
| **SHA-256 Checksum** | `749c90d720360a4215bb15345526073c079ba4cc95e3fa558796d083f85fce9e` |
| **Data Immutability Policy** | Read-only. Direct modifications, overwrites, or deletions are strictly prohibited. |

---

## 3. Dataset Dimensions & Schema Definition

- **Total Recorded Rows:** 48,204
- **Total Columns:** 9
- **Memory Footprint (In-Memory Pandas):** ~3.31 MB

### Column-Wise Schema & Physical Dtypes

| # | Column Name | Raw CSV Type | Pandas Dtype | Inferred Logical Data Type |
| :- | :--- | :--- | :--- | :--- |
| 1 | `holiday` | String / Text | `object` | Categorical (Nominal Holiday Indicator) |
| 2 | `temp` | Numeric / Float | `float64` | Continuous Numeric (Temperature in Kelvin) |
| 3 | `rain_1h` | Numeric / Float | `float64` | Continuous Numeric (Liquid precipitation in mm) |
| 4 | `snow_1h` | Numeric / Float | `float64` | Continuous Numeric (Snowfall accumulation in mm) |
| 5 | `clouds_all` | Numeric / Integer | `int64` | Discrete Numeric / Percentage (Cloud coverage 0–100%) |
| 6 | `weather_main` | String / Text | `object` | Categorical (Macro Weather Category) |
| 7 | `weather_description`| String / Text | `object` | Categorical (Granular Weather Description) |
| 8 | `date_time` | String / Text | `object` | Temporal Timestamp (`YYYY-MM-DD HH:MM:SS`) |
| 9 | `traffic_volume` | Numeric / Integer | `int64` | Discrete Numeric Target (Hourly Vehicle Count) |

---

## 4. Missing-Value Analysis & Ingestion Sensitivity

A vital data engineering finding relates to how nulls are represented in the raw data versus how analytical libraries parse them:

```
+---------------------------------------------------------------------------------------+
| Ingestion Mode         | Column   | Null Count | Null %  | Interpretation             |
+---------------------------------------------------------------------------------------+
| Raw Text (Strict CSV)  | All cols | 0          | 0.00%   | Zero empty delimiter cells |
| Default Pandas Ingestion| holiday  | 48,143     | 99.87%  | Literal string 'None' -> NaN |
| Default Pandas Ingestion| Other 8  | 0          | 0.00%   | Fully populated            |
+---------------------------------------------------------------------------------------+
```

### Confirmed Finding:
1. **Raw CSV Integrity:** There are **zero empty or missing fields** in the raw text file. Every row contains 9 comma-separated tokens.
2. **The `holiday` Ingestion Trap:** The column `holiday` uses the literal string `'None'` to designate standard non-holiday operating days. Because standard pandas `read_csv()` treats `'None'` as a default `NA` token, naive ingestion flags 48,143 rows (99.87%) as missing data.
3. **Data Quality Status:** This is **not missing data**; it is a valid domain value indicating normal traffic operations.

---

## 5. Duplicate Records & Timestamp Concurrency

The audit evaluated both full-record duplication and timestamp uniqueness:

### 5.1 Exact Row Duplicates
- **Confirmed Count:** **17 exact duplicate rows** where all 9 column values are identical.
- **Example:**
  - `2015-09-30 19:00:00 | temp: 286.29 | clouds: 75 | Clouds | broken clouds | volume: 3679` appears at rows 18696 and 18697.
  - `2016-06-01 10:00:00 | temp: 289.06 | clouds: 90 | Rain | moderate rain | volume: 4831` appears at rows 23850 and 23851.

### 5.2 Timestamp Multi-Reporting Concurrency
- **Total Unique Timestamps:** 40,575 distinct hourly slots across 48,204 total rows.
- **Timestamps with Multiple Records:** **5,445 timestamps** (13.42% of unique timestamps) account for **13,074 rows**.
- **Root Cause Analysis:** Meteorological sensors frequently record multiple simultaneous weather phenomena for the exact same hour and interstate segment (e.g., simultaneous `Rain: light rain` and `Drizzle: light intensity drizzle`). In all such instances, the target metric `traffic_volume` and temperature are identical.
- **Impact on Future Phases:** Direct ingestion into time-series forecasting algorithms without pre-aggregation will distort temporal sequences and cause artificial weighting.

---

## 6. Temporal Coverage & Time-Series Continuity

The date-time column was audited for format consistency, range, and temporal gaps:

- **Parsing Test:** 100% successful conversion using standard ISO format `%Y-%m-%d %H:%M:%S`. NaT (Not-a-Time) count is **0**.
- **Temporal Boundaries:**
  - **Earliest Timestamp:** `2012-10-02 09:00:00`
  - **Latest Timestamp:** `2018-09-30 23:00:00`
- **Total Timeline Span:** 2,189 calendar days (~5.99 years), equivalent to **52,551 hourly intervals**.
- **Populated Unique Hours:** 40,575 hours (77.21% coverage).
- **Missing Hourly Intervals:** **11,976 hours** (22.79% temporal absence).

### Major Temporal Discontinuities (Gaps)

```
Major Observation Gaps (> 3 Days):
1. 2014-08-08 01:00:00  -->  2015-06-11 20:00:00   [307 DAYS 19 HOURS GAP - Historical Blackout]
2. 2013-10-27 01:00:00  -->  2013-11-06 04:00:00   [10 DAYS 03 HOURS GAP]
3. 2015-06-14 20:00:00  -->  2015-06-19 18:00:00   [4 DAYS 22 HOURS GAP]
4. 2014-04-29 08:00:00  -->  2014-05-04 05:00:00   [4 DAYS 21 HOURS GAP]
5. 2015-10-23 11:00:00  -->  2015-10-27 08:00:00   [3 DAYS 21 HOURS GAP]
```

---

## 7. Numerical Feature Statistics

Parametric and non-parametric summary statistics calculated on the raw records:

| Feature | Min | Q1 (25%) | Median (50%) | Q3 (75%) | Max | Mean | Std Dev | Zero Count (%) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `temp` (K) | 0.00 | 272.16 | 282.45 | 291.81 | 310.07 | 281.21 | 13.34 | 10 (0.02%) |
| `rain_1h` (mm) | 0.00 | 0.00 | 0.00 | 0.00 | 9,831.30 | 0.33 | 44.79 | 44,737 (92.81%) |
| `snow_1h` (mm) | 0.00 | 0.00 | 0.00 | 0.00 | 0.51 | 0.0002 | 0.0082 | 48,141 (99.87%) |
| `clouds_all` (%) | 0.00 | 1.00 | 64.00 | 90.00 | 100.00 | 49.36 | 39.02 | 1,988 (4.12%) |
| `traffic_volume` | 0.00 | 1,193.00 | 3,380.00 | 4,933.00 | 7,280.00 | 3,259.82 | 1,986.86 | 2 (0.004%) |

### Conversions & Real-World Scales
- **Temperature:**
  - Min: 0.00 K (-273.15 °C / -459.67 °F) — **Physical Anomaly**
  - Q1: 272.16 K (-0.99 °C / 30.22 °F) — Sub-freezing winter/autumn threshold
  - Median: 282.45 K (9.30 °C / 48.74 °F)
  - Max: 310.07 K (36.92 °C / 98.46 °F) — Realistic peak summer high for Twin Cities

---

## 8. Categorical Feature Distributions

### 8.1 `holiday` Feature Distribution
- Total records: 48,204
- Normal operation days (`'None'`): 48,143 (99.87%)
- Official Holidays flagged: 61 records (0.13%)

```
Holiday Name                 Occurrences
----------------------------------------
Labor Day                              7
Christmas Day                          6
Thanksgiving Day                       6
Martin Luther King Jr Day              6
New Years Day                          6
Veterans Day                           5
Columbus Day                           5
Memorial Day                           5
Washingtons Birthday                   5
State Fair                             5
Independence Day                       5
```

### 8.2 `weather_main` Feature Distribution (11 Categories)
- `Clouds`: 15,164 (31.46%)
- `Clear`: 13,391 (27.78%)
- `Mist`: 5,950 (12.34%)
- `Rain`: 5,672 (11.77%)
- `Snow`: 2,876 (5.97%)
- `Drizzle`: 1,821 (3.78%)
- `Haze`: 1,360 (2.82%)
- `Thunderstorm`: 1,034 (2.15%)
- `Fog`: 912 (1.89%)
- `Smoke`: 20 (0.04%)
- `Squall`: 4 (0.01%)

### 8.3 `weather_description` Granularity (38 Categories)
Granular breakdown reveals text casing inconsistencies:
- `'sky is clear'`: 11,665 records (lowercase)
- `'Sky is Clear'`: 1,726 records (title-cased)
- `'SQUALLS'`: 4 records (all-caps)
- In Phase 2, string normalization (`.str.lower().str.strip()`) is required.

---

## 9. Anomaly & Outlier Deep-Dive

### 9.1 Temperature Sensor Failure: Absolute Zero (0.0 Kelvin)
- **Observations:** Exactly **10 records** contain `temp == 0.0`.
- **Occurrence Window:**
  - 4 consecutive hours on `2014-01-31` (03:00 to 06:00)
  - 6 consecutive hours on `2014-02-02` (03:00 to 08:00)
- **Context:** Clear skies (`weather_main: Clear`, `weather_description: sky is clear`). The surrounding valid readings on those dates are in the range of 250–260 Kelvin (-23 °C to -13 °C).
- **Diagnosis:** Complete sensor signal drop or transmission null recorded as numeric 0.

### 9.2 Extreme Precipitation Anomaly: `rain_1h = 9831.30 mm`
- **Observation:** Row index 24872 (`2016-07-11 17:00:00`) records `rain_1h = 9831.30 mm`.
- **Context:** `temp = 302.11 K`, `weather_main = Rain`, `weather_description = very heavy rain`, `traffic_volume = 5535`.
- **Diagnosis:** Physical impossibility. 9,831 mm corresponds to 9.83 meters (~32.25 feet) of rain in 60 minutes. The world-record 1-hour rainfall ever recorded on Earth is 305 mm (Holt, Missouri, 1947). The second-highest value in the entire dataset is `55.63 mm`. This is either a 100x scaling glitch or sensor counter corruption.

### 9.3 Zero Traffic Volume Records
- **Observations:** Exactly **2 records** report `traffic_volume == 0`:
  - `2016-07-23 18:00:00` (`weather_main: Rain`, non-holiday Saturday)
  - `2016-07-23 23:00:00` (`weather_main: Haze`, non-holiday Saturday)
- **Diagnosis:** Interstate 94 is a primary transcontinental highway. Zero traffic on a Saturday evening suggests either total interstate closure (e.g., major construction or severe accident) or sensor loop outage.

---

## 10. Target Metric Assessment (`traffic_volume`)

Is `traffic_volume` suitable as the primary target variable for machine learning, SQL analytics, and BI dashboards?

- **Distribution Profile:**
  - Range: [0, 7280] vehicles/hour
  - Mean: 3,259.82 | Median: 3,380.00
  - Standard Deviation: 1,986.86
  - Skewness: `-0.089` (near-zero symmetry)
  - Kurtosis: `-1.309` (platykurtic / bimodal peak structure)
- **Diurnal Traffic Signature:**
  - Trough: 02:00–03:00 (~370–388 vehicles/hour)
  - Morning Peak: 07:00 (~4,740 vehicles/hour)
  - Evening Commuter Peak: 16:00 (~5,664 vehicles/hour)
- **Conclusion:** **Highly suitable.** The target behaves consistently with real-world urban highway dynamics, exhibits robust variance, and provides high predictive value for operational intelligence.

---

## 11. Rigorous Separation of Findings, Recommendations & Assumptions

### Confirmed Findings (Observed from Real Data)
1. The CSV contains 48,204 rows and 9 columns with zero raw missing text values.
2. 17 exact full-row duplicate records exist.
3. 5,445 timestamps have multiple rows (13,074 rows total) caused by simultaneous weather observations.
4. The timeline has a 307-day continuous blackout from August 8, 2014 to June 11, 2015.
5. 10 records have `temp == 0.0 K` and 1 record has `rain_1h == 9831.3 mm`.
6. String casing inconsistencies exist in `weather_description` (`'sky is clear'` vs `'Sky is Clear'`).
7. Naive pandas ingestion marks 99.87% of `holiday` as NaN due to the token `'None'`.

### Recommended Actions (For Phase 2 Implementation)
1. **Raw Layer Preservation:** Never mutate `data/raw/Metro_Interstate_Traffic_Volume.csv`.
2. **Duplicate Remediation:** Drop the 17 exact duplicate rows during staging.
3. **Timestamp De-duplication Strategy:** For timestamps with multiple weather reports, define a deterministic aggregation policy:
   - Primary option: Select dominant weather condition (highest severity rank) or concatenate secondary weather conditions.
   - Preserve single hourly granularity for time-series models.
4. **Outlier Treatment:**
   - Impute or replace the 10 absolute-zero temperature values using localized time-series linear interpolation.
   - Cap or correct the 9,831.3 mm precipitation outlier using neighborhood temporal context or set to realistic upper bound.
5. **Categorical Normalization:**
   - Standardize `weather_description` to lowercase and trimmed strings.
   - Create explicit binary feature `is_holiday` (0/1) from `holiday != 'None'`.
6. **Date & Calendar Feature Engineering:**
   - Extract `hour`, `day_of_week`, `month`, `year`, `is_weekend`, and cyclical sine/cosine time representations.

### Documented Assumptions
1. The sensor location is westbound I-94 at MN DoT ATR station 301 near Minneapolis/St. Paul.
2. The unit of measurement for `temp` is Kelvin, `rain_1h` is millimeters, and `snow_1h` is millimeters of accumulation.
3. Traffic counts represent vehicles per hour across all westbound lanes at the recording gantry.

---

## 12. Risks and Limitations

| Risk / Limitation | Impact | Architectural Mitigation Plan |
| :--- | :--- | :--- |
| **307-Day Observation Gap** | Disrupts contiguous auto-regressive models (ARIMA/SARIMAX). | Segment modeling into pre-gap and post-gap regimes, or use tree-based regressors (XGBoost/LightGBM) with lag features conditioned on valid contiguous history. |
| **Multiple Records per Hour** | Biases group-by aggregations and inflates vehicle volume sums if unhandled. | Implement SQL staging deduplication / weather consolidation table prior to warehouse modeling. |
| **Rare Holiday Frequency** | Only 61 holiday hours across 6 years limit holiday-specific statistical power. | Group holidays into binary `is_holiday` indicator and analyze aggregate holiday behavioral shifts. |
