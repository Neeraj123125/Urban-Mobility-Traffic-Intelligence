# Data Cleaning & Transformation Decisions Log
## Urban Mobility & Traffic Intelligence — Phase 2

**Document Version:** 2.0.0 (Post-Verification Edition)  
**Verification Date:** September 15, 2026  
**Author:** Senior Data Engineer & Data Analytics Architect  
**Source Dataset:** `data/raw/Metro_Interstate_Traffic_Volume.csv` (SHA-256: `749c90d720360a4215bb15345526073c079ba4cc95e3fa558796d083f85fce9e`)  
**Interim Staging:** `data/interim/traffic_staged.csv` (48,187 rows, 9 columns)  
**Processed Target:** `data/processed/traffic_cleaned.csv` (40,575 rows, 24 columns)  
**Local Analytical Database:** `sql/traffic_intelligence.db` (SQLite validated)  

---

## 1. Explicit Dataset Grain Definition & Calendar Completeness

> ### [!IMPORTANT]
> **Definitive Dataset Grain:**  
> `data/processed/traffic_cleaned.csv` contains **exactly one row per OBSERVED hourly timestamp (40,575 unique records)**.  
> It does **NOT** contain one row for every calendar hour in the historical span.  
> Across the total timeline from `2012-10-02 09:00:00` to `2018-09-30 23:00:00` (52,551 calendar hours), there are **11,976 unrecorded hours** (22.79% of the span), including the major 307-day sensor blackout (August 2014 to June 2015). Missing calendar hours were **intentionally NOT synthetically imputed, zero-filled, or fabricated**, adhering strictly to engineering ground truth rules.

---

## 2. Ingestion & Schema Standardization

### 2.1 Preserving the Literal `'None'` in `holiday`
- **Issue:** Standard Python/Pandas parsing interprets the string literal `'None'` as a null token (`NaN`), incorrectly reporting that 99.87% of the dataset is missing.
- **Forensic Inspection:** Confirmed `'None'` designates normal, non-holiday baseline operations. Exactly 61 records in the raw data contain official holiday names (e.g., `'Labor Day'`, `'Christmas Day'`).
- **Decision:** Ingested using `keep_default_na=False` to preserve `'None'` as an explicit nominal category. Engineered a secondary binary indicator `is_holiday` (0 for `'None'`, 1 for official holidays).

### 2.2 Datetime Formatting & Column Nomenclature
- **Action:** Standardized all column names to strict lowercase `snake_case`.
- **Parsing:** Converted `date_time` using explicit format `YYYY-MM-DD HH:MM:SS`. 100% of rows parsed cleanly without a single `NaT` error.

---

## 3. Duplicate Records & Timestamp Concurrency Investigation

### 3.1 Exact Full-Row Duplicate Removal
- **Finding:** Forensic inspection identified **exactly 17 rows** where every single attribute (datetime, weather features, and traffic volume) was identical.
- **Decision:** Dropped the 17 redundant rows during initial staging. The dataset transitioned from 48,204 raw rows to 48,187 unique observation rows in `data/interim/traffic_staged.csv`.

### 3.2 Duplicate Timestamp Concurrency Analysis
After dropping exact duplicates, the audit revealed:
- **5,430 unique timestamps** appeared multiple times, accounting for **13,042 rows**.
- **Crucial Empirical Finding:** Across all 5,430 multi-record timestamps, **`traffic_volume` differed in ZERO instances (0%)**.
- **Double-Counting Prevention:**
  - Sum of volume across raw dataset: $157,136,284$ vehicles
  - Sum of volume across staged dataset: $157,071,219$ vehicles
  - Sum of volume across consolidated processed mart: **$133,518,143$ vehicles**
  - **Phantom Double-Counted Vehicles Prevented:** **$23,553,076$ vehicles (-17.64% volume inflation eliminated)**.

### 3.3 Hourly Grain Consolidation Rule: The Weather Severity Hierarchy
When multiple weather conditions were logged for the same hour, traffic operations are governed by the most adverse atmospheric event. We established the following deterministic severity hierarchy:

```
Rank 11: Thunderstorm  (Highest hazard / severe speed reduction)
Rank 10: Squall        (High wind / severe visibility hazard)
Rank  9: Snow          (Pavement friction loss / major delay driver)
Rank  8: Rain          (Hydroplaning risk / spray / delay driver)
Rank  7: Drizzle       (Wet pavement / minor spray)
Rank  6: Fog           (Severe visibility impairment)
Rank  5: Mist          (Moderate visibility impairment)
Rank  4: Haze          (Atmospheric scattering)
Rank  3: Smoke         (Localized particulate hazard)
Rank  2: Clouds        (Overcast / cloud cover)
Rank  1: Clear         (Optimal baseline driving conditions)
```

**Consolidation Implementation:**
- `traffic_volume`: Retain verified invariant single hourly count.
- `holiday`: Retain verified invariant holiday classification.
- `temp`: Arithmetic mean of recorded temperatures during that hour.
- `rain_1h` & `snow_1h`: Peak recorded hourly precipitation/snowfall (`max`).
- `weather_main` & `weather_description`: Dominant condition selected via the hierarchy.
- `weather_event_count`: Audit column tracking how many raw weather observations occurred during that hour.

---

## 4. Outlier & Invalid-Value Deep-Dive

### 4.1 Recheck of Extreme Rain Anomaly (`rain_1h = 9831.3 mm`)

- **Raw Record:** Row index 24872 (`2016-07-11 17:00:00`)
  - `date_time`: `2016-07-11 17:00:00`
  - `rain_1h`: **`9831.30 mm`**
  - `temp`: `302.11 K` (28.96 °C)
  - `weather_main`: `Rain`
  - `weather_description`: `very heavy rain`
  - `traffic_volume`: `5535`
- **Transformed Value:** **`55.63 mm`**
- **Statistical and Scientific Justification:**
  1. *Physical Impossibility:* 9,831.3 mm corresponds to 9.83 meters (~32.25 feet) of liquid rainfall in a single 60-minute window. The world-record 1-hour rainfall ever recorded on Earth is 305 mm (Holt, Missouri, 1947). 9,831 mm is clearly a sensor counter corruption or 100x/1000x scaling error.
  2. *Forensic Category Baseline:* There are exactly 18 records in the entire dataset classified as `'very heavy rain'`. Excluding row 24872, the remaining 17 valid records exhibit:
     - Minimum: `16.38 mm`
     - 25th Percentile: `18.80 mm`
     - Median: `21.42 mm`
     - Mean: `25.44 mm`
     - 75th Percentile: `27.57 mm`
     - **Maximum Valid Observation:** **`55.63 mm`** (recorded during a severe thunderstorm on `2013-08-07 02:00:00`).
  3. *Why Winsorization / Capping at 55.63 mm is Defensible:* Capping at `55.63 mm` treats the record as an extreme upper-bound cloudburst event. It preserves the adverse weather signal (heavy downpour impacting traffic) without introducing catastrophic variance inflation into regression models. Alternatively, imputing with the category median (`21.42 mm`) would also be defensible; however, capping at `55.63 mm` preserves the maximum legitimate meteorological intensity observed at this station.

---

### 4.2 Recheck of Absolute Zero Temperature (`temp == 0.0 K`)

- **Raw Records:** Exactly **10 records** contain `temp == 0.0 K` (-273.15 °C).
- **Physical Context:** Occurred during sub-zero Minnesota winter conditions in early 2014. Clear skies (`sky is clear`).
- **Forensic Inspection of Preceding & Following Valid Boundaries:**

#### Window 1: 2014-01-31 (4 Consecutive Hours)
- `2014-01-31 02:00:00` (Preceding Valid): `temp = 255.93 K` (-17.22 °C)
- `2014-01-31 03:00:00` (Raw: `0.0 K`) $\rightarrow$ Transformed: **`255.93 K`** (`volume = 361`)
- `2014-01-31 04:00:00` (Raw: `0.0 K`) $\rightarrow$ Transformed: **`255.93 K`** (`volume = 734`)
- `2014-01-31 05:00:00` (Raw: `0.0 K`) $\rightarrow$ Transformed: **`255.93 K`** (`volume = 2557`)
- `2014-01-31 06:00:00` (Raw: `0.0 K`) $\rightarrow$ Transformed: **`255.93 K`** (`volume = 5150`)
- `2014-01-31 07:00:00` (Following Valid): `temp = 255.93 K` (-17.22 °C)

*Causality & Data Leakage Assessment for Window 1:*
Because the temperature was identical (255.93 K) immediately before and immediately after the 4-hour dropout, a strictly causal **Forward Fill (Last Observation Carried Forward / LOCF)** produces the exact same value of **255.93 K**. Zero future information leaked.

#### Window 2: 2014-02-02 (6 Consecutive Hours)
- `2014-02-02 02:00:00` (Preceding Valid): `temp = 255.37 K` (-17.78 °C)
- `2014-02-02 03:00:00` (Raw: `0.0 K`) $\rightarrow$ Transformed: **`255.41 K`** (`volume = 291`)
- `2014-02-02 04:00:00` (Raw: `0.0 K`) $\rightarrow$ Transformed: **`255.44 K`** (`volume = 284`)
- `2014-02-02 05:00:00` (Raw: `0.0 K`) $\rightarrow$ Transformed: **`255.48 K`** (`volume = 434`)
- `2014-02-02 06:00:00` (Raw: `0.0 K`) $\rightarrow$ Transformed: **`255.51 K`** (`volume = 739`)
- `2014-02-02 07:00:00` (Raw: `0.0 K`) $\rightarrow$ Transformed: **`255.55 K`** (`volume = 962`)
- `2014-02-02 08:00:00` (Raw: `0.0 K`) $\rightarrow$ Transformed: **`255.58 K`** (`volume = 1670`)
- `2014-02-02 09:00:00` (Following Valid): `temp = 255.62 K` (-17.53 °C)

*Causality & Data Leakage Assessment for Window 2:*
- If strictly causal Forward Fill (LOCF) was used: `255.37 K` across all 6 hours.
- With linear interpolation: values transition smoothly from `255.41 K` to `255.58 K`.
- The maximum divergence between LOCF and linear interpolation is **$0.21 \text{ K}$ ($0.21 \text{ °C}$)**, which is well within sensor precision tolerances ($\pm 0.5 \text{ °C}$).
- **Forecasting Non-Leakage Confirmation:** Both windows occurred in early 2014—months before the August 2014 sensor blackout. In Phase 4, predictive modeling will be drawn from the post-blackout era (June 2015 – September 2018: 26,677 total observed hours; longest unbroken contiguous run: 1,915 consecutive hours). These 10 historical records from early 2014 do not reside in the test horizon and cause zero data leakage into future predictions.

---

### 4.3 Zero Traffic Volume (`traffic_volume == 0`)
- Exactly 2 records on Saturday `2016-07-23` (18:00 and 23:00).
- Surrounding hours logged 0 to 24 vehicles/hr during severe thunderstorms and fog.
- Retained unchanged as legitimate full highway closure / emergency detour edge cases.

---

## 5. Recalculated Operational Metrics

```
+-------------------------------------------------------------+-------------------+
| Metric Description                                          | Verified Value    |
+-------------------------------------------------------------+-------------------+
| 1. Raw Dataset Row Count                                    | 48,204 rows       |
| 2. Exact Full-Row Duplicate Count Dropped                   | 17 rows           |
| 3. Interim Staged Dataset Row Count                         | 48,187 rows       |
| 4. Unique Recorded Timestamps Count                         | 40,575 timestamps |
| 5. Final Processed Dataset Row Count                        | 40,575 rows       |
| 6. Final Processed Dataset Column Count                     | 24 columns        |
| 7. Duplicate Timestamps in Processed Dataset                | 0 (Strict 1-to-1) |
| 8. Timeline Span (Start to End)                             | 52,551 hours      |
|    • Earliest Observation                                   | 2012-10-02 09:00  |
|    • Latest Observation                                     | 2018-09-30 23:00  |
| 9. Missing Unobserved Calendar Hours                        | 11,976 hours      |
|    • Historical Sensor Blackout (Aug 8, 2014 - Jun 11, 2015)| 307 days 19 hours |
|    • Scattered Intermittent Maintenance Hours               | 2,185 hours       |
| 10. Double-Counted Phantom Vehicles Prevented               | 23,553,076 veh.   |
+-------------------------------------------------------------+-------------------+
```
