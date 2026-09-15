"""
Urban Mobility & Traffic Intelligence — Executive Analytics Dashboard
Phase 5: Decision-Oriented Executive & Portfolio Intelligence Layer

Technology Stack: Streamlit, Plotly, SQLite3, Pandas, NumPy, Joblib
Corridor: Interstate 94 Westbound (ATR Station 301), Minneapolis-St. Paul, Minnesota
Champion Forecasting Model: XGBoost Regressor (Test MAE: 130.84 veh/hr, sMAPE: 5.43%, R2: 0.9897)
"""

import os
import json
import sqlite3
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 1. APPLICATION CONFIGURATION & STYLING
st.set_page_config(
    page_title="Urban Mobility & Traffic Intelligence",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for executive aesthetic

st.markdown("""
<style>
    .main { background-color: #f8fafc; }
    .kpi-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    }
    .kpi-title {
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748b;
        margin-bottom: 4px;
    }
    .kpi-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 4px;
    }
    .kpi-subtitle {
        font-size: 0.80rem;
        color: #475569;
    }
    .section-header {
        font-size: 1.35rem;
        font-weight: 700;
        color: #1e293b;
        margin-top: 18px;
        margin-bottom: 14px;
        border-bottom: 2px solid #e2e8f0;
        padding-bottom: 6px;
    }
    .badge-champion {
        background-color: #dcfce7;
        color: #15803d;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.80rem;
    }
    .badge-baseline {
        background-color: #f1f5f9;
        color: #475569;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 500;
        font-size: 0.80rem;
    }
</style>
""", unsafe_allow_html=True)

DB_PATH = os.path.join("sql", "traffic_intelligence.db")
PROCESSED_DATA_PATH = os.path.join("data", "processed", "traffic_cleaned.csv")
CONFIG_PATH = os.path.join("models", "feature_config.json")
MODEL_PATH = os.path.join("models", "traffic_forecaster_best.joblib")


# 2. CACHED DATA LOADERS & QUERIES

@st.cache_data
def load_processed_data() -> pd.DataFrame:
    """Loads the single-source-of-truth processed dataset."""
    df = pd.read_csv(PROCESSED_DATA_PATH, parse_dates=["date_time"])
    return df.sort_values("date_time").reset_index(drop=True)


@st.cache_data
def query_sqlite(query: str) -> pd.DataFrame:
    """Executes a read-only query against the SQLite dimensional mart."""
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn)


@st.cache_data
def load_model_config() -> dict:
    """Loads Phase 4 machine learning metadata and performance benchmarks."""
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


# Load data assets
df_all = load_processed_data()
model_config = load_model_config()


# 3. GLOBAL SIDEBAR FILTERS

st.sidebar.image("https://img.icons8.com/fluency/96/traffic-light.png", width=64)
st.sidebar.title("Traffic Intelligence")
st.sidebar.caption("Westbound I-94 Corridor | MN DoT ATR 301")
st.sidebar.markdown("---")

# Navigation
page = st.sidebar.radio(
    "Navigation Menu",
    [
        "1. Executive Overview",
        "2. Traffic Pattern Analysis",
        "3. Weather Intelligence",
        "4. Forecasting & Model Benchmark",
        "5. Model Explainability & Insights"
    ],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.subheader("Interactive Corridor Filters")

# Date range filter
min_dt = df_all["date_time"].min().date()
max_dt = df_all["date_time"].max().date()

date_preset = st.sidebar.selectbox(
    "Date Presets",
    [
        "All Historical Data (2012-2018)",
        "Held-Out Test Period (Apr-Sep 2018)",
        "Post-Blackout Era (Jun 2015-Sep 2018)",
        "Pre-Blackout Era (Oct 2012-Aug 2014)",
        "Custom Range"
    ],
    index=0
)

if date_preset == "All Historical Data (2012-2018)":
    selected_start, selected_end = min_dt, max_dt
elif date_preset == "Held-Out Test Period (Apr-Sep 2018)":
    selected_start, selected_end = pd.to_datetime("2018-04-01").date(), max_dt
elif date_preset == "Post-Blackout Era (Jun 2015-Sep 2018)":
    selected_start, selected_end = pd.to_datetime("2015-06-11").date(), max_dt
elif date_preset == "Pre-Blackout Era (Oct 2012-Aug 2014)":
    selected_start, selected_end = min_dt, pd.to_datetime("2014-08-08").date()
else:
    selected_range = st.sidebar.date_input("Custom Date Range", [min_dt, max_dt])
    if len(selected_range) == 2:
        selected_start, selected_end = selected_range[0], selected_range[1]
    else:
        selected_start, selected_end = min_dt, max_dt

# Day type filter
day_type = st.sidebar.radio("Day Type", ["All Days", "Weekdays Only", "Weekends Only"], index=0)

# Hour slider
hour_range = st.sidebar.slider("Hour of Day", 0, 23, (0, 23))

# Weather filter
all_weather_conditions = sorted(df_all["weather_main"].dropna().unique().tolist())
selected_weather = st.sidebar.multiselect("Weather Conditions", all_weather_conditions, default=all_weather_conditions)

# Apply global filter logic
filtered_df = df_all[
    (df_all["date_time"].dt.date >= selected_start) &
    (df_all["date_time"].dt.date <= selected_end) &
    (df_all["hour"].between(hour_range[0], hour_range[1])) &
    (df_all["weather_main"].isin(selected_weather))
].copy()

if day_type == "Weekdays Only":
    filtered_df = filtered_df[filtered_df["is_weekend"] == 0]
elif day_type == "Weekends Only":
    filtered_df = filtered_df[filtered_df["is_weekend"] == 1]

st.sidebar.markdown("---")
st.sidebar.caption(f"Active Filtered Records: **{len(filtered_df):,}** / {len(df_all):,} ({len(filtered_df)/len(df_all)*100:.1f}%)")

# 4. PAGE 1: EXECUTIVE OVERVIEW & MOBILITY KPIS

if page == "1. Executive Overview":
    st.title("Executive Overview & Mobility KPIs")
    st.markdown("High-level operational intelligence for municipal transit planners, highway dispatchers, and mobility architects.")

    # Top KPI Row (3 columns x 3 metric cards = 9 KPIs)
    k1, k2, k3 = st.columns(3)
    k4, k5, k6 = st.columns(3)
    k7, k8, k9 = st.columns(3)

    avg_vol = filtered_df["traffic_volume"].mean() if not filtered_df.empty else 0
    peak_vol = filtered_df["traffic_volume"].max() if not filtered_df.empty else 0
    peak_dt = filtered_df.loc[filtered_df["traffic_volume"].idxmax(), "date_time"] if not filtered_df.empty else "N/A"

    morning_rush = filtered_df[filtered_df["is_morning_rush_hour"] == 1]["traffic_volume"].mean() if not filtered_df.empty else 0
    evening_rush = filtered_df[filtered_df["is_evening_rush_hour"] == 1]["traffic_volume"].mean() if not filtered_df.empty else 0

    weekday_avg = filtered_df[filtered_df["is_weekend"] == 0]["traffic_volume"].mean() if not filtered_df.empty else 0
    weekend_avg = filtered_df[filtered_df["is_weekend"] == 1]["traffic_volume"].mean() if not filtered_df.empty else 0
    weekend_delta = ((weekend_avg - weekday_avg) / weekday_avg * 100) if weekday_avg > 0 else 0

    clear_avg = filtered_df[filtered_df["weather_main"] == "Clear"]["traffic_volume"].mean() if not filtered_df.empty else 0

    with k1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Average Hourly Traffic</div>
            <div class="kpi-value">{avg_vol:,.1f} <span style="font-size: 1rem; font-weight: 500; color: #64748b;">veh/hr</span></div>
            <div class="kpi-subtitle">Observed baseline throughput</div>
        </div>
        """, unsafe_allow_html=True)

    with k2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Peak Observed Volume</div>
            <div class="kpi-value">{peak_vol:,.0f} <span style="font-size: 1rem; font-weight: 500; color: #64748b;">veh/hr</span></div>
            <div class="kpi-subtitle">Timestamp: {str(peak_dt)[:16]}</div>
        </div>
        """, unsafe_allow_html=True)

    with k3:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Peak Timestamp Record</div>
            <div class="kpi-value" style="font-size: 1.35rem; padding-top: 6px;">{str(peak_dt)[:16]}</div>
            <div class="kpi-subtitle">All-time record peak volume</div>
        </div>
        """, unsafe_allow_html=True)

    with k4:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Morning Rush Average</div>
            <div class="kpi-value">{morning_rush:,.1f} <span style="font-size: 1rem; font-weight: 500; color: #64748b;">veh/hr</span></div>
            <div class="kpi-subtitle">06:00–09:00 Mon–Fri commuter surge</div>
        </div>
        """, unsafe_allow_html=True)

    with k5:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Evening Rush Average</div>
            <div class="kpi-value">{evening_rush:,.1f} <span style="font-size: 1rem; font-weight: 500; color: #64748b;">veh/hr</span></div>
            <div class="kpi-subtitle">15:00–18:00 Mon–Fri commuter crest</div>
        </div>
        """, unsafe_allow_html=True)

    with k6:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Weekday vs. Weekend Delta</div>
            <div class="kpi-value" style="color: {'#dc2626' if weekend_delta < 0 else '#16a34a'};">{weekend_delta:+.1f}%</div>
            <div class="kpi-subtitle">Weekday: {weekday_avg:,.0f} | Weekend: {weekend_avg:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)

    with k7:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Clear Weather Baseline</div>
            <div class="kpi-value">{clear_avg:,.1f} <span style="font-size: 1rem; font-weight: 500; color: #64748b;">veh/hr</span></div>
            <div class="kpi-subtitle">Throughput under optimal sky conditions</div>
        </div>
        """, unsafe_allow_html=True)

    with k8:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Forecast Error (MAE)</div>
            <div class="kpi-value" style="color: #16a34a;">130.84 <span style="font-size: 1rem; font-weight: 500; color: #64748b;">veh/hr</span></div>
            <div class="kpi-subtitle">XGBoost Champion Model (Held-Out Test)</div>
        </div>
        """, unsafe_allow_html=True)

    with k9:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-title">Forecast Precision (sMAPE)</div>
            <div class="kpi-value" style="color: #16a34a;">5.43%</div>
            <div class="kpi-subtitle">Relative percentage error across all test hours</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div class=\"section-header\">Corridor Diurnal Signature: Weekdays vs. Weekends</div>", unsafe_allow_html=True)

    # Diurnal signature chart
    diurnal_df = filtered_df.groupby(["hour", "is_weekend"])["traffic_volume"].mean().reset_index()
    diurnal_df["Day Category"] = diurnal_df["is_weekend"].map({0: "Weekday (Mon-Fri)", 1: "Weekend (Sat-Sun)"})

    fig_diurnal = px.line(
        diurnal_df,
        x="hour",
        y="traffic_volume",
        color="Day Category",
        color_discrete_map={"Weekday (Mon-Fri)": "#1f77b4", "Weekend (Sat-Sun)": "#ff7f0e"},
        markers=True,
        labels={"hour": "Hour of Day (00:00 to 23:00)", "traffic_volume": "Mean Traffic Volume (Vehicles/Hour)"},
        title="Hourly Corridor Throughput Profile"
    )
    fig_diurnal.update_layout(
        xaxis=dict(tickmode="linear", tick0=0, dtick=1),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=40, t=50, b=40)
    )
    st.plotly_chart(fig_diurnal, width="stretch")

    # Master KPI Scorecard Table
    st.markdown("<div class=\"section-header\">Master Enterprise KPI Scorecard (From SQLite Mart)</div>", unsafe_allow_html=True)
    try:
        kpi_table = query_sqlite("SELECT kpi_metric_name AS [KPI Metric], kpi_metric_value AS [Value], kpi_context AS [Operational Context] FROM vw_executive_kpi_summary")
        st.dataframe(kpi_table, hide_index=True, width="stretch")
    except Exception as e:
        st.warning(f"Could not load SQLite view: {e}")


# 5. PAGE 2: TRAFFIC PATTERN ANALYSIS


elif page == "2. Traffic Pattern Analysis":
    st.title("Traffic Pattern Analysis")
    st.markdown("Detailed exploration of temporal rhythms, commuter peaks, seasonality, and volume distributions.")

    col1, col2 = st.columns(2)

    with col1:
        # Day of week ranking
        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_df = filtered_df.groupby("day_name")["traffic_volume"].agg(["mean", "count"]).reindex(dow_order).reset_index()
        dow_df.columns = ["Day of Week", "Mean Volume", "Sample Hours"]

        fig_dow = px.bar(
            dow_df,
            x="Day of Week",
            y="Mean Volume",
            color="Mean Volume",
            color_continuous_scale="Blues",
            title="Weekly Traffic Volume Ranking"
        )
        fig_dow.update_layout(coloraxis_showscale=False, margin=dict(l=30, r=30, t=40, b=30))
        st.plotly_chart(fig_dow, width="stretch")

    with col2:
        # Monthly Seasonality
        month_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        month_df = filtered_df.groupby("month_name")["traffic_volume"].mean().reindex(month_order).reset_index()
        month_df.columns = ["Month", "Mean Volume"]

        fig_month = px.line(
            month_df,
            x="Month",
            y="Mean Volume",
            markers=True,
            title="Annual Monthly Seasonality Profile",
            line_shape="spline"
        )
        fig_month.update_traces(line_color="#2ca02c", marker=dict(size=8, color="#1e7e34"))
        fig_month.update_layout(margin=dict(l=30, r=30, t=40, b=30))
        st.plotly_chart(fig_month, width="stretch")

    # Congestion Extremes Callout
    st.markdown("<div class=\"section-header\">Traffic Extremes: High Congestion vs. Nocturnal Free-Flow</div>", unsafe_allow_html=True)
    c_peak, c_low = st.columns(2)

    peak_hours_count = len(filtered_df[filtered_df["traffic_volume"] >= 6000])
    low_hours_count = len(filtered_df[filtered_df["traffic_volume"] <= 500])

    with c_peak:
        st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #dc2626;">
            <div class="kpi-title" style="color: #dc2626;">Severe Congestion Periods (Volume ≥ 6,000 veh/hr)</div>
            <div class="kpi-value">{peak_hours_count:,} <span style="font-size: 1rem; color: #64748b;">observed hours</span></div>
            <div class="kpi-subtitle">Represents {peak_hours_count/max(len(filtered_df),1)*100:.1f}% of active observations. Heavily concentrated in weekday evening rush (16:00-17:00).</div>
        </div>
        """, unsafe_allow_html=True)

    with c_low:
        st.markdown(f"""
        <div class="kpi-card" style="border-left: 4px solid #2563eb;">
            <div class="kpi-title" style="color: #2563eb;">Nocturnal Free-Flow Periods (Volume ≤ 500 veh/hr)</div>
            <div class="kpi-value">{low_hours_count:,} <span style="font-size: 1rem; color: #64748b;">observed hours</span></div>
            <div class="kpi-subtitle">Represents {low_hours_count/max(len(filtered_df),1)*100:.1f}% of active observations. Optimal window for highway maintenance (01:00-04:00).</div>
        </div>
        """, unsafe_allow_html=True)

    # Hourly Volatility (Standard Deviation & CV)
    st.markdown("<div class=\"section-header\">Hourly Volatility Index (Coefficient of Variation)</div>", unsafe_allow_html=True)
    vol_df = filtered_df.groupby("hour")["traffic_volume"].agg(["mean", "std"]).reset_index()
    vol_df["cv"] = vol_df["std"] / vol_df["mean"]
    vol_df.columns = ["Hour", "Mean Volume", "Std Dev", "Coefficient of Variation (CV)"]

    fig_vol = px.bar(
        vol_df,
        x="Hour",
        y="Coefficient of Variation (CV)",
        color="Coefficient of Variation (CV)",
        color_continuous_scale="Reds",
        title="Traffic Variability Across 24 Hours (Higher CV = Less Predictable Flow)"
    )
    fig_vol.update_layout(xaxis=dict(tickmode="linear", tick0=0, dtick=1), margin=dict(l=30, r=30, t=40, b=30))
    st.plotly_chart(fig_vol, width="stretch")


# 6. PAGE 3: WEATHER INTELLIGENCE

elif page == "3. Weather Intelligence":
    st.title("Weather Intelligence & Atmospheric Sensitivity")
    st.info("Observational Framing: Meteorological metrics reflect observed correlations along the I-94 corridor. Observational data indicates throughput degradation during adverse conditions but does not assert isolated physical causation.")

    col1, col2 = st.columns(2)

    with col1:
        # Macro weather categories
        weather_summary = filtered_df.groupby("weather_main")["traffic_volume"].agg(["mean", "count"]).reset_index()
        weather_summary.columns = ["Weather Condition", "Mean Volume", "Sample Hours"]
        weather_summary = weather_summary.sort_values("Mean Volume", ascending=True)

        fig_weather = px.bar(
            weather_summary,
            x="Mean Volume",
            y="Weather Condition",
            orientation="h",
            color="Mean Volume",
            color_continuous_scale="Viridis",
            title="Observed Mean Traffic Volume by Macro Weather Condition"
        )
        fig_weather.update_layout(coloraxis_showscale=False, margin=dict(l=30, r=30, t=40, b=30))
        st.plotly_chart(fig_weather, width="stretch")

    with col2:
        # Thermal sensitivity bands
        temp_bands = pd.cut(
            filtered_df["temp_celsius"],
            bins=[-50, -10, 0, 15, 25, 60],
            labels=["Extreme Cold (< -10°C)", "Freezing (-10°C to 0°C)", "Mild (0°C to 15°C)", "Warm (15°C to 25°C)", "High Heat (> 25°C)"]
        )
        temp_df = filtered_df.groupby(temp_bands, observed=False)["traffic_volume"].agg(["mean", "count"]).reset_index()
        temp_df.columns = ["Thermal Band", "Mean Volume", "Sample Hours"]

        fig_temp = px.bar(
            temp_df,
            x="Thermal Band",
            y="Mean Volume",
            color="Mean Volume",
            color_continuous_scale="Thermal",
            title="Observed Traffic Volume Across Temperature Regimes"
        )
        fig_temp.update_layout(coloraxis_showscale=False, margin=dict(l=30, r=30, t=40, b=30))
        st.plotly_chart(fig_temp, width="stretch")

    # Rain Intensity & Weather Severity
    st.markdown("<div class=\"section-header\">Precipitation Impact & Meteorological Severity Hierarchy</div>", unsafe_allow_html=True)
    c_rain, c_sev = st.columns(2)

    with c_rain:
        rain_tiers = pd.cut(
            filtered_df["rain_1h"],
            bins=[-1, 0.001, 2.5, 7.6, 100],
            labels=["No Rain (0 mm)", "Light Rain (0-2.5 mm)", "Moderate (2.5-7.6 mm)", "Heavy (> 7.6 mm)"]
        )
        rain_df = filtered_df.groupby(rain_tiers, observed=False)["traffic_volume"].agg(["mean", "count"]).reset_index()
        rain_df.columns = ["Precipitation Tier", "Mean Volume", "Sample Hours"]

        fig_rain = px.bar(
            rain_df,
            x="Precipitation Tier",
            y="Mean Volume",
            color="Mean Volume",
            color_continuous_scale="Teal",
            title="Precipitation Intensity Tiers vs. Throughput"
        )
        fig_rain.update_layout(coloraxis_showscale=False, margin=dict(l=30, r=30, t=40, b=30))
        st.plotly_chart(fig_rain, width="stretch")

    with c_sev:
        # Weather event concurrency
        event_df = filtered_df.groupby("weather_event_count")["traffic_volume"].agg(["mean", "count"]).reset_index()
        event_df.columns = ["Concurrent Weather Events", "Mean Volume", "Sample Hours"]

        fig_event = px.bar(
            event_df,
            x="Concurrent Weather Events",
            y="Mean Volume",
            color="Mean Volume",
            color_continuous_scale="Purples",
            title="Multi-Weather Event Concurrency Impact"
        )
        fig_event.update_layout(coloraxis_showscale=False, margin=dict(l=30, r=30, t=40, b=30))
        st.plotly_chart(fig_event, width="stretch")


# 7. PAGE 4: FORECASTING & MODEL PERFORMANCE (XGBOOST CHAMPION)


elif page == "4. Forecasting & Model Benchmark":
    st.title("Forecasting Intelligence & Model Performance")
    st.markdown("""
    <div style="background-color: #ecfdf5; border-left: 5px solid #10b981; padding: 12px 18px; border-radius: 6px; margin-bottom: 20px;">
        <span class="badge-champion">CHAMPION MODEL</span>
        <strong style="color: #065f46; font-size: 1.05rem; margin-left: 8px;">XGBoost Regressor</strong>
        <span style="color: #047857; margin-left: 12px;">Held-Out Test MAE: <strong>130.84 veh/hr</strong> | sMAPE: <strong>5.43%</strong> | R²: <strong>0.9897</strong></span>
    </div>
    """, unsafe_allow_html=True)

    # Benchmark comparison scorecard
    st.markdown("<div class=\"section-header\">Forecasting Benchmark Scorecard (Held-Out Test Set: Apr-Sep 2018, N=4,386)</div>", unsafe_allow_html=True)
    bench_data = pd.DataFrame(model_config.get("test_performance", []))
    if not bench_data.empty:
        bench_data = bench_data.rename(columns={
            "model": "Model / Baseline",
            "mae": "MAE (veh/hr)",
            "rmse": "RMSE (veh/hr)",
            "smape": "sMAPE (%)",
            "r2": "R² Score",
            "n": "Test Records (N)"
        })
        st.dataframe(bench_data, hide_index=True, width="stretch")

    # Actual vs Predicted Time-Series Overlay
    st.markdown("<div class=\"section-header\">Actual vs. Predicted Forecast Overlay (Held-Out Test Set Window)</div>", unsafe_allow_html=True)
    st.image("reports/figures/13_pred_vs_actual_timeseries.png", width="stretch")

    # Error Diagnostics: Residuals & Parity
    st.markdown("<div class=\"section-header\">Residual Distribution & Parity Analysis</div>", unsafe_allow_html=True)
    c_diag1, c_diag2 = st.columns(2)
    with c_diag1:
        st.image("reports/figures/14_residuals_distribution_qq.png", width="stretch")
    with c_diag2:
        st.image("reports/figures/15_residuals_by_hour_day.png", width="stretch")

    # Operational Slices Table
    st.markdown("<div class=\"section-header\">Granular Operational Slices (XGBoost Accuracy Across Traffic Regimes)</div>", unsafe_allow_html=True)
    slice_data = pd.DataFrame(model_config.get("slice_performance", []))
    if not slice_data.empty:
        slice_data = slice_data.rename(columns={
            "slice": "Mobility Operational Slice",
            "mae": "MAE (veh/hr)",
            "rmse": "RMSE (veh/hr)",
            "smape": "sMAPE (%)",
            "r2": "R² Score",
            "n": "Test Records (N)"
        })
        st.dataframe(slice_data, hide_index=True, width="stretch")

    # Walk-Forward Cross-Validation Table
    st.markdown("<div class=\"section-header\">Expanding-Window Walk-Forward Validation (Historical Folds)</div>", unsafe_allow_html=True)
    wf_raw = model_config.get("walk_forward_cv", {})
    wf_rows = []
    if "xgboost" in wf_raw and "seasonal_naive" in wf_raw:
        for i in range(len(wf_raw["xgboost"])):
            fold_xgb = wf_raw["xgboost"][i]
            fold_sn = wf_raw["seasonal_naive"][i]
            wf_rows.append({
                "Fold": fold_xgb.get("fold", i + 1),
                "Seasonal Naive MAE": fold_sn.get("mae"),
                "Seasonal Naive sMAPE (%)": fold_sn.get("smape"),
                "XGBoost MAE": fold_xgb.get("mae"),
                "XGBoost sMAPE (%)": fold_xgb.get("smape"),
                "XGBoost R²": fold_xgb.get("r2"),
                "Validation Hours": fold_xgb.get("n")
            })
        st.dataframe(pd.DataFrame(wf_rows), hide_index=True, width="stretch")


# -----------------------------------------------------------------------------
# 8. PAGE 5: MODEL EXPLAINABILITY & INSIGHTS
# -----------------------------------------------------------------------------
elif page == "5. Model Explainability & Insights":
    st.title("Model Explainability & Strategic Mobility Insights")
    st.info("Explainability Context: Feature attributions are derived using SHAP (TreeExplainer). Feature importances quantify predictive contribution to model forecasts and do not represent standalone causal effects.")

    # SHAP Feature Importance Visual
    st.markdown("<div class=\"section-header\">Top Predictive Drivers: SHAP Feature Importance</div>", unsafe_allow_html=True)
    st.image("reports/figures/16_shap_feature_importance.png", width="stretch")

    # Top Features Table
    shap_top = pd.DataFrame(model_config.get("top_10_features", []))
    if not shap_top.empty:
        shap_top.columns = ["Feature Identifier", "Mean Absolute SHAP Value (veh/hr)"]
        shap_top["Mean Absolute SHAP Value (veh/hr)"] = shap_top["Mean Absolute SHAP Value (veh/hr)"].round(2)
        st.dataframe(shap_top, hide_index=True, width="stretch")

    # Decision-Oriented Q&A Section
    st.markdown("<div class=\"section-header\">Decision-Oriented Strategic Mobility Insights</div>", unsafe_allow_html=True)

    with st.expander("1. When is interstate traffic most congested along westbound I-94?", expanded=True):
        st.markdown("""
        - **Commuter Crest:** Traffic peaks during the non-holiday weekday evening rush (**15:00 to 18:00**), reaching an average volume of **5,544.75 vehicles/hour**.
        - **Absolute Peak Hour:** The single highest volume hour on record is **16:00 (4:00 PM)**, with a corridor-wide average of **5,708.61 vehicles/hour** and an all-time peak of **7,280 vehicles** on Thursday, March 9, 2017.
        - **Inbound Surge:** Morning rush (**06:00 to 09:00**) represents the second major crest, averaging **5,463.33 vehicles/hour**.
        """)

    with st.expander("2. Which hours require the most operational attention and ramp metering?", expanded=True):
        st.markdown("""
        - **Surge Window (05:00 to 07:00):** Highway volume experiences its sharpest surge between 05:00 and 06:00 (**+2,357 vehicles/hour** in a single 60-minute window). Active ramp metering and incident patrols should be fully activated prior to 05:30.
        - **Evening Saturation (15:30 to 17:30):** Operating closest to highway capacity threshold, making the corridor most vulnerable to bottleneck breakdown.
        """)

    with st.expander("3. How different are weekday and weekend travel patterns?", expanded=True):
        st.markdown("""
        - **Throughput Drop:** Weekend operations average **2,623.93 vehicles/hour**, representing a **-26.24% reduction** compared to weekday operations (**3,557.44 vehicles/hour**).
        - **Shift from Bimodal to Unimodal:** Weekday traffic displays a sharp bimodal curve (twin commuter peaks). Weekend traffic shifts into a smooth, unimodal leisure curve that peaks mid-afternoon (12:00 to 15:00) at ~4,100 veh/hr.
        """)

    with st.expander("4. What patterns are observed during adverse meteorological conditions?", expanded=True):
        st.markdown("""
        - **Severe Squalls & Snow:** Severe snow squalls coincide with an average volume drop of up to **-86.25%** (falling to 420 veh/hr) due to severe speed reduction and voluntary trip cancellation.
        - **Dense Fog:** Dense fog coincides with a **-19.36% throughput reduction** (2,653.77 vs. 3,055.16 veh/hr baseline).
        - **Heavy Rainfall:** Downpours exceeding 7.6 mm/hour correspond to a **-9.7% volume drop**, primarily driven by increased vehicle headways and reduced safe travel speeds.
        """)

    with st.expander("5. How accurately can next-hour traffic volume be forecasted?", expanded=True):
        st.markdown("""
        - **Champion Accuracy:** The production XGBoost model predicts next-hour traffic with an **MAE of 130.84 vehicles/hour** and an **sMAPE of 5.43%** ($R^2 = 0.9897$).
        - **Rush-Hour Dependability:** During high-density commuter peaks, forecast precision improves to **3.28% sMAPE** (Evening Rush) and **3.30% sMAPE** (Morning Rush), providing dependable intelligence for dynamic speed harmonization.
        """)

    with st.expander("6. Which features contribute most to forecasting accuracy?", expanded=True):
        st.markdown(r"""
        - **Diurnal Harmonics (`hour_cos`):** Mean |SHAP| = **918.97 veh/hr**. Represents the primary 24-hour day/night cycle.
        - **Short-Term Momentum (`traffic_lag_1h`):** Mean |SHAP| = **601.66 veh/hr**. Immediate prior state captures real-time persistence.
        - **Weekly Recurrence (`traffic_lag_168h`):** Mean |SHAP| = **190.75 veh/hr**. Aligns demand with the exact same hour of the preceding week.
        - **Rolling Boundaries (`traffic_roll_min_6h`):** Mean |SHAP| = **93.26 veh/hr**. Anchors recovery velocity from nocturnal lulls.
        """)

# 9. FOOTER
st.markdown("---")
st.caption("Urban Mobility & Traffic Intelligence Platform | Industrial Data Engineering, Dimensional Warehousing & Machine Learning Forecasting | Phase 5")
