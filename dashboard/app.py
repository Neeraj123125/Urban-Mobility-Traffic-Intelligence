"""
Urban Mobility & Traffic Intelligence — Command Center Dashboard
Phase 5: Executive Intelligence & Portfolio Intelligence Layer

Architecture: Streamlit, Plotly, SQLite3, Pandas, NumPy, Joblib
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

# -----------------------------------------------------------------------------
# 1. PAGE SETUP & SOPHISTICATED DARK COMMAND-CENTER THEME
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Urban Mobility | Traffic Intelligence Command Center",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Deep Charcoal / Near-Black Command Center Styling
st.markdown("""
<style>
    /* Global Base */
    html, body, [data-testid="stAppViewContainer"] {
        background-color: #0b0f17 !important;
        color: #e2e8f0 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }
    
    [data-testid="stHeader"] {
        background-color: rgba(11, 15, 23, 0.90) !important;
        backdrop-filter: blur(10px);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    [data-testid="stSidebar"] {
        background-color: #0e1422 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }
    
    /* Sidebar Brand & Navigation Styling */
    .sidebar-brand {
        padding: 8px 4px 18px 4px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        margin-bottom: 16px;
    }
    .brand-title {
        font-size: 1.10rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        color: #ffffff;
        line-height: 1.25;
        margin: 0;
    }
    .brand-title span {
        color: #00e5ff;
    }
    .brand-subtitle {
        font-size: 0.72rem;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #64748b;
        margin-top: 4px;
    }
    
    .sidebar-model-status {
        background: rgba(20, 27, 45, 0.85);
        border: 1px solid rgba(0, 229, 255, 0.25);
        border-radius: 8px;
        padding: 12px 14px;
        margin-top: 24px;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
    }
    
    /* Hero Header */
    .hero-container {
        background: linear-gradient(135deg, rgba(20, 27, 45, 0.95) 0%, rgba(14, 20, 34, 0.95) 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-left: 4px solid #00e5ff;
        border-radius: 10px;
        padding: 24px 28px;
        margin-bottom: 22px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
    }
    .hero-status {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        color: #10b981;
        background: rgba(16, 185, 129, 0.12);
        border: 1px solid rgba(16, 185, 129, 0.3);
        padding: 3px 10px;
        border-radius: 20px;
        margin-bottom: 12px;
    }
    .hero-title {
        font-size: 2.1rem;
        font-weight: 900;
        letter-spacing: -0.02em;
        line-height: 1.15;
        color: #ffffff;
        margin: 0 0 6px 0;
    }
    .hero-title span {
        color: #00e5ff;
    }
    .hero-subtitle {
        font-size: 0.98rem;
        color: #cbd5e1;
        margin: 0 0 10px 0;
        max-width: 900px;
    }
    .hero-meta {
        font-size: 0.78rem;
        color: #64748b;
        letter-spacing: 0.04em;
    }
    
    /* Command Center KPI Card */
    .kpi-card {
        background: #141b2d;
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 10px;
        padding: 16px 18px;
        min-height: 118px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25);
        transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
    }
    .kpi-card:hover {
        border-color: rgba(0, 229, 255, 0.45);
        transform: translateY(-2px);
        box-shadow: 0 8px 22px rgba(0, 229, 255, 0.10);
    }
    .kpi-label {
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #94a3b8;
    }
    .kpi-value {
        font-size: 1.95rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #ffffff;
        line-height: 1.1;
        margin: 4px 0 2px 0;
    }
    .kpi-sub {
        font-size: 0.76rem;
        color: #64748b;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    .card-badge {
        display: inline-block;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        padding: 2px 7px;
        border-radius: 4px;
        border: 1px solid;
    }
    
    /* Section Headers */
    .section-title-wrap {
        margin: 28px 0 16px 0;
        display: flex;
        align-items: baseline;
        gap: 12px;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding-bottom: 8px;
    }
    .section-title {
        font-size: 1.25rem;
        font-weight: 800;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: #ffffff;
        margin: 0;
    }
    .section-subtitle {
        font-size: 0.82rem;
        color: #64748b;
        margin: 0;
    }
    
    /* Insight Panel */
    .insight-card {
        background: #141b2d;
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 12px;
    }
    .insight-title {
        font-size: 0.88rem;
        font-weight: 700;
        color: #38bdf8;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .insight-body {
        font-size: 0.84rem;
        color: #cbd5e1;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

DB_PATH = os.path.join("sql", "traffic_intelligence.db")
PROCESSED_DATA_PATH = os.path.join("data", "processed", "traffic_cleaned.csv")
CONFIG_PATH = os.path.join("models", "feature_config.json")
MODEL_PATH = os.path.join("models", "traffic_forecaster_best.joblib")


# -----------------------------------------------------------------------------
# 2. CACHED DATA LOADERS
# -----------------------------------------------------------------------------
@st.cache_data
def load_processed_data() -> pd.DataFrame:
    """Loads single source of truth processed dataset."""
    df = pd.read_csv(PROCESSED_DATA_PATH, parse_dates=["date_time"])
    return df.sort_values("date_time").reset_index(drop=True)


@st.cache_data
def query_sqlite(query: str) -> pd.DataFrame:
    """Queries relational SQLite dimensional mart."""
    with sqlite3.connect(DB_PATH) as conn:
        return pd.read_sql_query(query, conn)


@st.cache_data
def load_model_config() -> dict:
    """Loads Phase 4 machine learning metadata and benchmark evaluations."""
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


df_all = load_processed_data()
model_config = load_model_config()


# -----------------------------------------------------------------------------
# 3. PLOTLY UNIFIED DARK THEME HELPER
# -----------------------------------------------------------------------------
def style_plotly_figure(fig, title=None, height=380):
    """Applies a clean, modern dark-mode command center palette to Plotly figures."""
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="rgba(20, 27, 45, 0.6)",
        plot_bgcolor="rgba(0, 0, 0, 0)",
        font=dict(
            family='-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            color="#94a3b8",
            size=11
        ),
        title=dict(
            text=title or "",
            font=dict(color="#f8fafc", size=14, family="sans-serif"),
            x=0.01,
            y=0.96
        ) if title else None,
        margin=dict(l=35, r=25, t=45 if title else 20, b=35),
        height=height,
        hoverlabel=dict(
            bgcolor="#1e293b",
            bordercolor="#00e5ff",
            font=dict(color="#ffffff", size=12)
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#cbd5e1", size=11),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    fig.update_xaxes(
        gridcolor="rgba(255, 255, 255, 0.06)",
        zerolinecolor="rgba(255, 255, 255, 0.12)",
        tickfont=dict(color="#94a3b8", size=10)
    )
    fig.update_yaxes(
        gridcolor="rgba(255, 255, 255, 0.06)",
        zerolinecolor="rgba(255, 255, 255, 0.12)",
        tickfont=dict(color="#94a3b8", size=10)
    )
    return fig


def render_kpi_card(
    label: str,
    value: str,
    subtitle: str,
    accent: str = "#00e5ff",
    badge: str = None
):
    """Renders a high-contrast executive KPI card."""
    badge_html = (
        f'<span class="card-badge" style="border-color: {accent}; color: {accent};">{badge}</span>'
        if badge else ''
    )

    html_content = (
        f'<div class="kpi-card">'
        f'<div style="display: flex; justify-content: space-between; align-items: center;">'
        f'<div class="kpi-label">{label}</div>'
        f'{badge_html}'
        f'</div>'
        f'<div class="kpi-value" style="color: {accent};">{value}</div>'
        f'<div class="kpi-sub">{subtitle}</div>'
        f'</div>'
    )
    st.markdown(html_content, unsafe_allow_html=True)


def render_section_header(title: str, subtitle: str = None):
    """Renders a standardized section header."""
    sub_html = f'<span class="section-subtitle">{subtitle}</span>' if subtitle else ''
    header_html = (
        f'<div class="section-title-wrap">'
        f'<h2 class="section-title">{title}</h2>'
        f'{sub_html}'
        f'</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# 4. REDESIGNED COMMAND CENTER SIDEBAR
# -----------------------------------------------------------------------------
st.sidebar.markdown(
    '<div class="sidebar-brand">'
    '<div class="brand-title">URBAN MOBILITY<br><span>INTELLIGENCE</span></div>'
    '<div class="brand-subtitle">Command Center &bull; I-94 Westbound</div>'
    '</div>',
    unsafe_allow_html=True
)

# Navigation Menu
page = st.sidebar.radio(
    "Navigation Menu",
    [
        "01  Executive Overview",
        "02  Traffic Patterns",
        "03  Weather Intelligence",
        "04  Forecasting Intelligence",
        "05  Model Explainability"
    ],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("<div style='font-size: 0.78rem; font-weight: 700; color: #94a3b8; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 12px;'>CORRIDOR CONTROLS</div>", unsafe_allow_html=True)

# Date Presets & Range
min_dt = df_all["date_time"].min().date()
max_dt = df_all["date_time"].max().date()

date_preset = st.sidebar.selectbox(
    "Date Filter Preset",
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
    selected_range = st.sidebar.date_input("Custom Calendar Range", [min_dt, max_dt])
    if len(selected_range) == 2:
        selected_start, selected_end = selected_range[0], selected_range[1]
    else:
        selected_start, selected_end = min_dt, max_dt

# Day Type & Hour Filters
day_type = st.sidebar.radio("Day Type", ["All Days", "Weekdays Only", "Weekends Only"], index=0)
hour_range = st.sidebar.slider("Hour Window (00:00 - 23:00)", 0, 23, (0, 23))

# Weather Filter
all_weather_conditions = sorted(df_all["weather_main"].dropna().unique().tolist())
selected_weather = st.sidebar.multiselect("Atmospheric Conditions", all_weather_conditions, default=all_weather_conditions)

# Reactive Filtering Engine
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

st.sidebar.markdown(
    f"<div style='font-size: 0.74rem; color: #64748b; margin-top: 8px;'>"
    f"Active Records: <strong style='color: #e2e8f0;'>{len(filtered_df):,}</strong> / {len(df_all):,} ({len(filtered_df)/len(df_all)*100:.1f}%)"
    f"</div>",
    unsafe_allow_html=True
)

# Compact Model Status Card in Sidebar
st.sidebar.markdown(
    '<div class="sidebar-model-status">'
    '<div style="font-size: 0.68rem; letter-spacing: 0.10em; font-weight: 700; text-transform: uppercase; color: #94a3b8; margin-bottom: 3px;">MODEL STATUS</div>'
    '<div style="font-size: 0.95rem; font-weight: 800; color: #00e5ff; display: flex; align-items: center; gap: 6px;">'
    '<span style="color: #10b981; font-size: 0.75rem;">●</span> XGBoost Champion'
    '</div>'
    '<div style="display: flex; justify-content: space-between; margin-top: 8px; font-size: 0.78rem; color: #cbd5e1; border-top: 1px solid rgba(255,255,255,0.08); padding-top: 6px;">'
    '<span>MAE: <strong style="color: #ffffff;">130.84</strong></span>'
    '<span>sMAPE: <strong style="color: #ffffff;">5.43%</strong></span>'
    '</div>'
    '</div>',
    unsafe_allow_html=True
)


# -----------------------------------------------------------------------------
# 5. PAGE 1: EXECUTIVE OVERVIEW
# -----------------------------------------------------------------------------
if page == "01  Executive Overview":
    # Hero Section
    st.markdown(
        '<div class="hero-container">'
        '<div class="hero-status"><span style="color: #10b981;">●</span> SYSTEM ONLINE &bull; I-94 WESTBOUND CORRIDOR</div>'
        '<h1 class="hero-title">URBAN MOBILITY<br><span>TRAFFIC INTELLIGENCE</span></h1>'
        '<p class="hero-subtitle">Data-driven traffic patterns, weather intelligence and machine-learning forecasting.</p>'
        '<div class="hero-meta">Historical traffic intelligence &bull; 2012–2018 &bull; XGBoost forecasting &bull; MN DoT ATR Station 301</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # Dynamic metrics calculation from active filter
    avg_vol = filtered_df["traffic_volume"].mean() if not filtered_df.empty else 0
    peak_vol = filtered_df["traffic_volume"].max() if not filtered_df.empty else 0
    peak_idx = filtered_df["traffic_volume"].idxmax() if not filtered_df.empty else None
    peak_dt_str = str(filtered_df.loc[peak_idx, "date_time"])[:16] if peak_idx is not None else "N/A"
    peak_fmt = f"{peak_dt_str[5:10]} &bull; {peak_dt_str[11:16]}" if peak_idx is not None else "N/A"

    # Primary Row: 4 Essential KPI Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card("AVERAGE TRAFFIC", f"{avg_vol:,.1f}", "vehicles / hour", accent="#00e5ff")
    with k2:
        render_kpi_card("PEAK TRAFFIC", f"{peak_vol:,.0f}", peak_fmt, accent="#38bdf8")
    with k3:
        render_kpi_card("FORECAST MAE", "130.84", "vehicles / hour", accent="#10b981", badge="XGBOOST")
    with k4:
        render_kpi_card("FORECAST sMAPE", "5.43%", "held-out test period", accent="#10b981", badge="R² = 0.9897")

    # Secondary Commuter & Operational Row: 4 Cards
    morning_rush = filtered_df[filtered_df["is_morning_rush_hour"] == 1]["traffic_volume"].mean() if not filtered_df.empty else 0
    evening_rush = filtered_df[filtered_df["is_evening_rush_hour"] == 1]["traffic_volume"].mean() if not filtered_df.empty else 0
    weekday_avg = filtered_df[filtered_df["is_weekend"] == 0]["traffic_volume"].mean() if not filtered_df.empty else 0
    weekend_avg = filtered_df[filtered_df["is_weekend"] == 1]["traffic_volume"].mean() if not filtered_df.empty else 0
    weekend_delta = ((weekend_avg - weekday_avg) / weekday_avg * 100) if weekday_avg > 0 else 0
    clear_avg = filtered_df[filtered_df["weather_main"] == "Clear"]["traffic_volume"].mean() if not filtered_df.empty else 0

    k5, k6, k7, k8 = st.columns(4)
    with k5:
        render_kpi_card("MORNING RUSH", f"{morning_rush:,.1f}", "06:00–09:00 Mon–Fri surge", accent="#e2e8f0")
    with k6:
        render_kpi_card("EVENING RUSH", f"{evening_rush:,.1f}", "15:00–18:00 Mon–Fri crest", accent="#e2e8f0")
    with k7:
        delta_color = "#f43f5e" if weekend_delta < 0 else "#10b981"
        render_kpi_card("WEEKEND SHIFT", f"{weekend_delta:+.1f}%", f"Weekday {weekday_avg:,.0f} | Wkd {weekend_avg:,.0f}", accent=delta_color)
    with k8:
        render_kpi_card("CLEAR WEATHER", f"{clear_avg:,.1f}", "optimal sky throughput", accent="#e2e8f0")

    # Main Trend: Corridor Diurnal Signature Chart
    render_section_header("CORRIDOR DIURNAL FLOW", "Hourly throughput profile across active time window")

    diurnal_df = filtered_df.groupby(["hour", "is_weekend"])["traffic_volume"].mean().reset_index()
    diurnal_df["Day Category"] = diurnal_df["is_weekend"].map({0: "Weekday (Mon-Fri)", 1: "Weekend (Sat-Sun)"})

    fig_diurnal = px.line(
        diurnal_df,
        x="hour",
        y="traffic_volume",
        color="Day Category",
        color_discrete_map={"Weekday (Mon-Fri)": "#00e5ff", "Weekend (Sat-Sun)": "#f59e0b"},
        markers=True,
        labels={"hour": "Hour of Day (00:00 - 23:00)", "traffic_volume": "Vehicles / Hour"}
    )
    fig_diurnal.update_traces(line=dict(width=2.5), marker=dict(size=6))
    fig_diurnal.update_layout(xaxis=dict(tickmode="linear", tick0=0, dtick=1))
    style_plotly_figure(fig_diurnal, height=360)
    st.plotly_chart(fig_diurnal, width="stretch")

    # Analytical Split: Commuter Peak Insights & Forecast Benchmark Summary
    render_section_header("EXECUTIVE MOBILITY SUMMARY", "Core operational insights and model verification")
    c_ins1, c_ins2 = st.columns(2)

    with c_ins1:
        st.markdown(
            '<div class="insight-card" style="border-left: 4px solid #00e5ff;">'
            '<div class="insight-title">Corridor Congestion & Peak Windows</div>'
            '<div class="insight-body">'
            '&bull; <strong>Evening Commuter Peak:</strong> Traffic reaches its absolute corridor maximum at <strong>16:00 (4:00 PM)</strong> averaging <strong>5,708.61 veh/hr</strong>, with the overall evening commute averaging 5,544.75 veh/hr.<br>'
            '&bull; <strong>Morning Inbound Surge:</strong> The sharpest hour-over-hour acceleration occurs between 05:00 and 06:00 (+2,357 veh/hr in 60 minutes), cresting at 07:00 (4,740.20 veh/hr).<br>'
            '&bull; <strong>Weekend Leisure Shift:</strong> Overall weekend throughput drops by <strong>-26.24%</strong>, transitioning from a bimodal twin-peak commuter shape into a smooth unimodal curve peaking at 14:00.'
            '</div>'
            '</div>',
            unsafe_allow_html=True
        )

    with c_ins2:
        st.markdown(
            '<div class="insight-card" style="border-left: 4px solid #10b981;">'
            '<div class="insight-title">Forecasting Power (XGBoost Champion)</div>'
            '<div class="insight-body">'
            '&bull; <strong>75.78% Error Reduction:</strong> XGBoost reduces test error from 540.22 veh/hr (Seasonal Naive baseline) down to <strong>130.84 veh/hr</strong> ($R^2 = 0.9897$).<br>'
            '&bull; <strong>Rush-Hour Precision:</strong> During critical morning and evening commuter windows, forecasting sMAPE is <strong>3.30%</strong> and <strong>3.28%</strong> respectively.<br>'
            '&bull; <strong>Zero Systematic Bias:</strong> Mean residual error on held-out data is <strong>-1.34 veh/hr</strong>, providing transit dispatchers with unbiased forward intelligence.'
            '</div>'
            '</div>',
            unsafe_allow_html=True
        )

    # Master KPI Scorecard Table (From SQLite)
    render_section_header("ENTERPRISE WAREHOUSE KPI SCORECARD", "Directly queried from relational dimensional view (vw_executive_kpi_summary)")
    try:
        kpi_table = query_sqlite("SELECT kpi_metric_name AS [KPI Metric], kpi_metric_value AS [Value], kpi_context AS [Operational Context] FROM vw_executive_kpi_summary")
        st.dataframe(kpi_table, hide_index=True, width="stretch")
    except Exception as e:
        st.warning(f"Could not load SQLite view: {e}")


# -----------------------------------------------------------------------------
# 6. PAGE 2: TRAFFIC PATTERN ANALYSIS
# -----------------------------------------------------------------------------
elif page == "02  Traffic Patterns":
    st.markdown(
        '<div class="hero-container" style="padding: 18px 24px; margin-bottom: 20px;">'
        '<div class="hero-status" style="color: #38bdf8; background: rgba(56, 189, 248, 0.12); border-color: rgba(56, 189, 248, 0.3);">ANALYTICAL DEEP-DIVE</div>'
        '<h2 style="font-size: 1.6rem; font-weight: 800; color: #ffffff; margin: 0;">TRAFFIC RHYTHMS & COMMUTER DYNAMICS</h2>'
        '<div style="font-size: 0.85rem; color: #94a3b8; margin-top: 4px;">Diurnal signatures, weekday/weekend distribution, monthly seasonality, and volume volatility.</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # 1. TRAFFIC RHYTHM & COMMUTER RUSH
    render_section_header("TRAFFIC RHYTHM", "24-hour diurnal volume distribution across all observed days")
    
    hourly_stats = filtered_df.groupby("hour")["traffic_volume"].agg(["mean", "median", lambda x: x.quantile(0.25), lambda x: x.quantile(0.75)]).reset_index()
    hourly_stats.columns = ["hour", "mean_vol", "median_vol", "q25", "q75"]

    fig_rhythm = go.Figure()
    fig_rhythm.add_trace(go.Scatter(
        x=hourly_stats["hour"], y=hourly_stats["q75"],
        mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"
    ))
    fig_rhythm.add_trace(go.Scatter(
        x=hourly_stats["hour"], y=hourly_stats["q25"],
        mode="lines", line=dict(width=0), fill="tonexty", fillcolor="rgba(0, 229, 255, 0.12)",
        name="IQR (25th - 75th Percentile)"
    ))
    fig_rhythm.add_trace(go.Scatter(
        x=hourly_stats["hour"], y=hourly_stats["mean_vol"],
        mode="lines+markers", line=dict(color="#00e5ff", width=2.5),
        marker=dict(size=6, color="#00e5ff"), name="Mean Volume"
    ))
    fig_rhythm.add_trace(go.Scatter(
        x=hourly_stats["hour"], y=hourly_stats["median_vol"],
        mode="lines", line=dict(color="#38bdf8", width=1.8, dash="dot"),
        name="Median Volume"
    ))
    fig_rhythm.update_layout(xaxis=dict(tickmode="linear", tick0=0, dtick=1))
    style_plotly_figure(fig_rhythm, height=350)
    st.plotly_chart(fig_rhythm, width="stretch")

    # 2. WEEKLY MOBILITY PATTERN & SEASONALITY (2 Columns)
    render_section_header("WEEKLY MOBILITY PATTERN & SEASONALITY", "Day-of-week ranking and annual monthly curve")
    col_w1, col_w2 = st.columns(2)

    with col_w1:
        dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        dow_df = filtered_df.groupby("day_name")["traffic_volume"].agg(["mean", "count"]).reindex(dow_order).reset_index()
        dow_df.columns = ["Day of Week", "Mean Volume", "Sample Hours"]

        fig_dow = px.bar(
            dow_df, x="Day of Week", y="Mean Volume",
            color="Mean Volume", color_continuous_scale=["#141b2d", "#00e5ff"],
            labels={"Mean Volume": "Mean Volume (veh/hr)"}
        )
        fig_dow.update_layout(coloraxis_showscale=False)
        style_plotly_figure(fig_dow, title="Weekly Day-of-Week Throughput Ranking", height=320)
        st.plotly_chart(fig_dow, width="stretch")

    with col_w2:
        month_order = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        month_df = filtered_df.groupby("month_name")["traffic_volume"].mean().reindex(month_order).reset_index()
        month_df.columns = ["Month", "Mean Volume"]

        fig_month = px.line(
            month_df, x="Month", y="Mean Volume", markers=True,
            line_shape="spline", labels={"Mean Volume": "Vehicles / Hour"}
        )
        fig_month.update_traces(line_color="#10b981", line_width=2.5, marker=dict(size=7, color="#34d399"))
        style_plotly_figure(fig_month, title="Monthly Seasonality Profile (Annual Curve)", height=320)
        st.plotly_chart(fig_month, width="stretch")

    # 3. EXTREMES & VOLATILITY
    render_section_header("TRAFFIC EXTREMES & HOURLY VOLATILITY", "Severe congestion thresholds and coefficient of variation")
    c_p1, c_p2 = st.columns(2)

    peak_count = len(filtered_df[filtered_df["traffic_volume"] >= 6000])
    low_count = len(filtered_df[filtered_df["traffic_volume"] <= 500])

    with c_p1:
        render_kpi_card("SEVERE CONGESTION (≥ 6,000)", f"{peak_count:,}", f"{peak_count/max(len(filtered_df),1)*100:.1f}% of observed hours &bull; Evening peak concentrated", accent="#f43f5e")
    with c_p2:
        render_kpi_card("NOCTURNAL FREE-FLOW (≤ 500)", f"{low_count:,}", f"{low_count/max(len(filtered_df),1)*100:.1f}% of observed hours &bull; Primary maintenance window", accent="#38bdf8")

    # Volatility Bar Chart (CV)
    vol_df = filtered_df.groupby("hour")["traffic_volume"].agg(["mean", "std"]).reset_index()
    vol_df["cv"] = vol_df["std"] / vol_df["mean"]
    vol_df.columns = ["Hour", "Mean Volume", "Std Dev", "CV"]

    fig_vol = px.bar(
        vol_df, x="Hour", y="CV", color="CV",
        color_continuous_scale=["#141b2d", "#f59e0b", "#f43f5e"],
        labels={"CV": "Coefficient of Variation (σ / μ)"}
    )
    fig_vol.update_layout(coloraxis_showscale=False, xaxis=dict(tickmode="linear", tick0=0, dtick=1))
    style_plotly_figure(fig_vol, title="Hourly Traffic Volatility Index (Higher CV = Less Predictable Flow)", height=300)
    st.plotly_chart(fig_vol, width="stretch")


# -----------------------------------------------------------------------------
# 7. PAGE 3: WEATHER INTELLIGENCE
# -----------------------------------------------------------------------------
elif page == "03  Weather Intelligence":
    st.markdown(
        '<div class="hero-container" style="padding: 18px 24px; margin-bottom: 20px;">'
        '<div class="hero-status" style="color: #00e5ff; background: rgba(0, 229, 255, 0.12); border-color: rgba(0, 229, 255, 0.3);">METEOROLOGICAL SENSITIVITY</div>'
        '<h2 style="font-size: 1.6rem; font-weight: 800; color: #ffffff; margin: 0;">ATMOSPHERIC IMPACT INTELLIGENCE</h2>'
        '<div style="font-size: 0.85rem; color: #94a3b8; margin-top: 4px;">Observed volume relationships across precipitation, freezing regimes, and weather hazard rankings.</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # Observational framing callout
    st.markdown(
        '<div style="background: rgba(20, 27, 45, 0.90); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 3px solid #38bdf8; border-radius: 6px; padding: 10px 16px; margin-bottom: 18px; font-size: 0.82rem; color: #cbd5e1;">'
        '<strong>Observational Framing:</strong> Meteorological metrics reflect observed correlations along the I-94 corridor. Observational data indicates significant throughput degradation during adverse conditions but does not assert isolated physical causation.'
        '</div>',
        unsafe_allow_html=True
    )

    # Macro Weather Impact & Temperature Regimes (2 Columns)
    render_section_header("WEATHER PHENOMENA & THERMAL REGIMES", "Volume variance across macro weather categories and temperature bands")
    col_wea1, col_wea2 = st.columns(2)

    with col_wea1:
        wea_summary = filtered_df.groupby("weather_main")["traffic_volume"].agg(["mean", "count"]).reset_index()
        wea_summary.columns = ["Weather Condition", "Mean Volume", "Sample Hours"]
        wea_summary = wea_summary.sort_values("Mean Volume", ascending=True)

        fig_wea = px.bar(
            wea_summary, x="Mean Volume", y="Weather Condition", orientation="h",
            color="Mean Volume", color_continuous_scale=["#f43f5e", "#f59e0b", "#00e5ff"],
            labels={"Mean Volume": "Mean Volume (veh/hr)"}
        )
        fig_wea.update_layout(coloraxis_showscale=False)
        style_plotly_figure(fig_wea, title="Observed Throughput by Macro Weather Condition", height=340)
        st.plotly_chart(fig_wea, width="stretch")

    with col_wea2:
        temp_bands = pd.cut(
            filtered_df["temp_celsius"],
            bins=[-50, -10, 0, 15, 25, 60],
            labels=["Extreme Cold (< -10°C)", "Freezing (-10°C to 0°C)", "Mild (0°C to 15°C)", "Warm (15°C to 25°C)", "High Heat (> 25°C)"]
        )
        temp_df = filtered_df.groupby(temp_bands, observed=False)["traffic_volume"].agg(["mean", "count"]).reset_index()
        temp_df.columns = ["Thermal Band", "Mean Volume", "Sample Hours"]

        fig_temp = px.bar(
            temp_df, x="Thermal Band", y="Mean Volume",
            color="Mean Volume", color_continuous_scale=["#38bdf8", "#00e5ff", "#f59e0b"],
            labels={"Mean Volume": "Mean Volume (veh/hr)"}
        )
        fig_temp.update_layout(coloraxis_showscale=False)
        style_plotly_figure(fig_temp, title="Throughput Across Temperature Regimes", height=340)
        st.plotly_chart(fig_temp, width="stretch")

    # Precipitation Intensity & Multi-Event Concurrency (2 Columns)
    render_section_header("PRECIPITATION INTENSITY & CONCURRENCY", "Impact of rainfall tiers and simultaneous atmospheric events")
    col_pr1, col_pr2 = st.columns(2)

    with col_pr1:
        rain_tiers = pd.cut(
            filtered_df["rain_1h"],
            bins=[-1, 0.001, 2.5, 7.6, 100],
            labels=["Dry (0 mm)", "Light (0-2.5 mm)", "Moderate (2.5-7.6 mm)", "Heavy (> 7.6 mm)"]
        )
        rain_df = filtered_df.groupby(rain_tiers, observed=False)["traffic_volume"].agg(["mean", "count"]).reset_index()
        rain_df.columns = ["Precipitation Tier", "Mean Volume", "Sample Hours"]

        fig_rain = px.bar(
            rain_df, x="Precipitation Tier", y="Mean Volume",
            color="Mean Volume", color_continuous_scale=["#00e5ff", "#38bdf8", "#6366f1"],
            labels={"Mean Volume": "Mean Volume (veh/hr)"}
        )
        fig_rain.update_layout(coloraxis_showscale=False)
        style_plotly_figure(fig_rain, title="Precipitation Intensity Tiers vs. Throughput", height=300)
        st.plotly_chart(fig_rain, width="stretch")

    with col_pr2:
        event_df = filtered_df.groupby("weather_event_count")["traffic_volume"].agg(["mean", "count"]).reset_index()
        event_df.columns = ["Concurrent Events", "Mean Volume", "Sample Hours"]

        fig_ev = px.bar(
            event_df, x="Concurrent Events", y="Mean Volume",
            color="Mean Volume", color_continuous_scale=["#141b2d", "#818cf8"],
            labels={"Mean Volume": "Mean Volume (veh/hr)"}
        )
        fig_ev.update_layout(coloraxis_showscale=False)
        style_plotly_figure(fig_ev, title="Multi-Weather Event Concurrency Impact", height=300)
        st.plotly_chart(fig_ev, width="stretch")


# -----------------------------------------------------------------------------
# 8. PAGE 4: FORECASTING & MODEL PERFORMANCE (XGBOOST CHAMPION)
# -----------------------------------------------------------------------------
elif page == "04  Forecasting Intelligence":
    st.markdown(
        '<div class="hero-container" style="padding: 18px 24px; margin-bottom: 20px;">'
        '<div class="hero-status" style="color: #10b981; background: rgba(16, 185, 129, 0.12); border-color: rgba(16, 185, 129, 0.3);">MODEL VERIFICATION</div>'
        '<h2 style="font-size: 1.6rem; font-weight: 800; color: #ffffff; margin: 0;">PREDICTIVE FORECASTING INTELLIGENCE</h2>'
        '<div style="font-size: 0.85rem; color: #94a3b8; margin-top: 4px;">XGBoost champion model benchmark, actual vs. predicted tracking, error diagnostics, and walk-forward cross-validation.</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # 1. FORECAST PERFORMANCE KPIs (Top Row)
    render_section_header("FORECAST PERFORMANCE (HELD-OUT TEST PERIOD: APR - SEP 2018)", "Evaluated on 4,386 completely untouched chronological hours")
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        render_kpi_card("TEST MAE", "130.84", "vehicles / hour error", accent="#00e5ff", badge="CHAMPION")
    with f2:
        render_kpi_card("TEST RMSE", "200.80", "root mean squared error", accent="#38bdf8")
    with f3:
        render_kpi_card("TEST sMAPE", "5.43%", "symmetric percentage error", accent="#10b981")
    with f4:
        render_kpi_card("R² SCORE", "0.9897", "variance explained", accent="#10b981")

    # 2. MODEL BENCHMARK TABLE
    render_section_header("MODEL BENCHMARK SCORECARD", "Comparison across statistical baselines, SARIMAX, LightGBM, and XGBoost")
    bench_data = pd.DataFrame(model_config.get("test_performance", []))
    if not bench_data.empty:
        bench_data = bench_data.rename(columns={
            "model": "Model / Baseline", "mae": "MAE (veh/hr)", "rmse": "RMSE (veh/hr)",
            "smape": "sMAPE (%)", "r2": "R² Score", "n": "Test Records (N)"
        })
        st.dataframe(bench_data, hide_index=True, width="stretch")

    # 3. ACTUAL VS PREDICTED TIME-SERIES OVERLAY
    render_section_header("ACTUAL VS. PREDICTED TIME-SERIES TRACE", "Multi-week test set window showing tight adherence across commuter cycles")
    st.image("reports/figures/13_pred_vs_actual_timeseries.png", width="stretch")

    # 4. RESIDUAL DIAGNOSTICS & PARITY (2 Columns)
    render_section_header("RESIDUAL DIAGNOSTICS & ERROR DISTRIBUTIONS", "Symmetrical zero-bias error verification")
    c_d1, c_d2 = st.columns(2)
    with c_d1:
        st.image("reports/figures/14_residuals_distribution_qq.png", width="stretch")
    with c_d2:
        st.image("reports/figures/15_residuals_by_hour_day.png", width="stretch")

    # 5. FORECAST ACCURACY BY TRAFFIC CONDITION (Operational Slices)
    render_section_header("FORECAST ACCURACY BY TRAFFIC CONDITION", "Slice evaluation across morning rush, evening rush, high traffic, weekdays, and weekends")
    slice_data = pd.DataFrame(model_config.get("slice_performance", []))
    if not slice_data.empty:
        slice_data = slice_data.rename(columns={
            "slice": "Mobility Operational Slice", "mae": "MAE (veh/hr)", "rmse": "RMSE (veh/hr)",
            "smape": "sMAPE (%)", "r2": "R² Score", "n": "Sample Hours (N)"
        })
        st.dataframe(slice_data, hide_index=True, width="stretch")

    # 6. WALK-FORWARD EXPANDING-WINDOW VALIDATION
    render_section_header("WALK-FORWARD EXPANDING-WINDOW VALIDATION", "3-fold temporal cross-validation with zero future lookahead leakage")
    wf_raw = model_config.get("walk_forward_cv", {})
    wf_rows = []
    if "xgboost" in wf_raw and "seasonal_naive" in wf_raw:
        for i in range(len(wf_raw["xgboost"])):
            f_xgb = wf_raw["xgboost"][i]
            f_sn = wf_raw["seasonal_naive"][i]
            wf_rows.append({
                "Fold Horizon": f"Fold {f_xgb.get('fold', i+1)}",
                "Seasonal Naive MAE": f"{f_sn.get('mae'):.2f}",
                "Seasonal Naive sMAPE (%)": f"{f_sn.get('smape'):.2f}%",
                "XGBoost MAE": f"{f_xgb.get('mae'):.2f}",
                "XGBoost sMAPE (%)": f"{f_xgb.get('smape'):.2f}%",
                "XGBoost R²": f"{f_xgb.get('r2'):.4f}",
                "Validation Hours": f"{f_xgb.get('n'):,}"
            })
        st.dataframe(pd.DataFrame(wf_rows), hide_index=True, width="stretch")


# -----------------------------------------------------------------------------
# 9. PAGE 5: MODEL EXPLAINABILITY & INSIGHTS
# -----------------------------------------------------------------------------
elif page == "05  Model Explainability":
    st.markdown(
        '<div class="hero-container" style="padding: 18px 24px; margin-bottom: 20px;">'
        '<div class="hero-status" style="color: #818cf8; background: rgba(129, 140, 248, 0.12); border-color: rgba(129, 140, 248, 0.3);">MODEL INTERPRETABILITY</div>'
        '<h2 style="font-size: 1.6rem; font-weight: 800; color: #ffffff; margin: 0;">WHY DOES THE MODEL PREDICT THIS?</h2>'
        '<div style="font-size: 0.85rem; color: #94a3b8; margin-top: 4px;">Feature attributions derived from SHAP (TreeExplainer) quantifying predictive model contributors (non-causal).</div>'
        '</div>',
        unsafe_allow_html=True
    )

    # Top Predictive Drivers
    render_section_header("TOP PREDICTIVE DRIVERS", "Top 15 model contributors ranked by Mean Absolute SHAP value on held-out test data")
    st.image("reports/figures/16_shap_feature_importance.png", width="stretch")

    # Table of Top 10 Drivers
    shap_top = pd.DataFrame(model_config.get("top_10_features", []))
    if not shap_top.empty:
        shap_top.columns = ["Predictive Feature Identifier", "Mean Absolute SHAP Value (veh/hr)"]
        shap_top["Mean Absolute SHAP Value (veh/hr)"] = shap_top["Mean Absolute SHAP Value (veh/hr)"].round(2)
        st.dataframe(shap_top, hide_index=True, width="stretch")

    # Feature Families Interpretation Panel
    render_section_header("FEATURE FAMILY ATTRIBUTION BREAKDOWN", "Analytical interpretation of top feature groupings")
    c_f1, c_f2 = st.columns(2)

    with c_f1:
        st.markdown(
            '<div class="insight-card">'
            '<div class="insight-title">1. Diurnal Harmonics & Hour of Day</div>'
            '<div class="insight-body">'
            '&bull; <strong>hour_cos (Mean |SHAP| = 918.97 veh/hr):</strong> The strongest single feature in the entire system. Governs the 24-hour circular day/night harmonic, anchoring the macro cyclical baseline.<br>'
            '&bull; <strong>hour (Mean |SHAP| = 90.68 veh/hr) & hour_sin (56.57 veh/hr):</strong> Reinforce discrete rush-hour step changes and fine-tune morning surge and evening crest gradients.'
            '</div>'
            '</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="insight-card">'
            '<div class="insight-title">2. Short-Term Flow Momentum</div>'
            '<div class="insight-body">'
            '&bull; <strong>traffic_lag_1h (Mean |SHAP| = 601.66 veh/hr):</strong> Second most influential feature. Captures immediate preceding corridor throughput, injecting real-time persistence and shock detection.<br>'
            '&bull; <strong>traffic_lag_2h & lag_4h:</strong> Provide secondary autoregressive smoothing to isolate single-observation transient noise.'
            '</div>'
            '</div>',
            unsafe_allow_html=True
        )

    with c_f2:
        st.markdown(
            '<div class="insight-card">'
            '<div class="insight-title">3. Weekly Seasonal Anchor</div>'
            '<div class="insight-body">'
            '&bull; <strong>traffic_lag_168h (Mean |SHAP| = 190.75 veh/hr):</strong> Matches the exact same hour of the preceding week (7 days ago). Acts as a vital calendar anchor distinguishing Monday commute demand from Saturday leisure flow.'
            '</div>'
            '</div>',
            unsafe_allow_html=True
        )

        st.markdown(
            '<div class="insight-card">'
            '<div class="insight-title">4. Past-Only Rolling Volume Bounds</div>'
            '<div class="insight-body">'
            '&bull; <strong>traffic_roll_min_6h (Mean |SHAP| = 93.26 veh/hr):</strong> Tracks the depth of nocturnal lull periods, establishing the baseline acceleration rate during the 05:00 surge.<br>'
            '&bull; <strong>traffic_roll_max_6h (Mean |SHAP| = 79.12 veh/hr):</strong> Indicates whether highway capacity is already operating near saturation.'
            '</div>'
            '</div>',
            unsafe_allow_html=True
        )

    # Strategic Decision-Oriented Q&A
    render_section_header("DECISION-ORIENTED MOBILITY Q&A", "Validated answers for municipal transportation planners and DOT dispatchers")

    with st.expander("When is traffic most congested along westbound I-94?", expanded=True):
        st.markdown("""
        - **Commuter Crest:** Traffic peaks during the non-holiday weekday evening rush (**15:00 to 18:00**), reaching an average volume of **5,544.75 vehicles/hour**.
        - **Absolute Peak Hour:** The single highest volume hour on record is **16:00 (4:00 PM)**, with a corridor-wide average of **5,708.61 vehicles/hour** and an all-time peak of **7,280 vehicles** on Thursday, March 9, 2017.
        - **Inbound Surge:** Morning rush (**06:00 to 09:00**) represents the second major crest, averaging **5,463.33 vehicles/hour**.
        """)

    with st.expander("Which hours require the most operational attention and ramp metering?", expanded=True):
        st.markdown("""
        - **Surge Window (05:00 to 07:00):** Highway volume experiences its sharpest surge between 05:00 and 06:00 (**+2,357 vehicles/hour** in a single 60-minute window). Active ramp metering and incident patrols should be fully activated prior to 05:30.
        - **Evening Saturation (15:30 to 17:30):** Operating closest to highway capacity threshold, making the corridor most vulnerable to bottleneck breakdown.
        """)

    with st.expander("How different are weekday and weekend travel patterns?", expanded=True):
        st.markdown("""
        - **Throughput Drop:** Weekend operations average **2,623.93 vehicles/hour**, representing a **-26.24% reduction** compared to weekday operations (**3,557.44 vehicles/hour**).
        - **Shift from Bimodal to Unimodal:** Weekday traffic displays a sharp bimodal curve (twin commuter peaks). Weekend traffic shifts into a smooth, unimodal leisure curve that peaks mid-afternoon (12:00 to 15:00) at ~4,100 veh/hr.
        """)

    with st.expander("What patterns are associated with adverse weather?", expanded=True):
        st.markdown("""
        - **Severe Squalls & Snow:** Severe snow squalls coincide with an average volume drop of up to **-86.25%** (falling to 420 veh/hr) due to severe speed reduction and voluntary trip cancellation.
        - **Dense Fog:** Dense fog coincides with a **-19.36% throughput reduction** (2,653.77 vs. 3,055.16 veh/hr baseline).
        - **Heavy Rainfall:** Downpours exceeding 7.6 mm/hour correspond to a **-9.7% volume drop**, primarily driven by increased vehicle headways and reduced safe travel speeds.
        """)

    with st.expander("How accurately can traffic be forecast?", expanded=True):
        st.markdown("""
        - **Champion Accuracy:** The production XGBoost model predicts next-hour traffic with an **MAE of 130.84 vehicles/hour** and an **sMAPE of 5.43%** ($R^2 = 0.9897$).
        - **Rush-Hour Dependability:** During high-density commuter peaks, forecast precision improves to **3.28% sMAPE** (Evening Rush) and **3.30% sMAPE** (Morning Rush), providing dependable intelligence for dynamic speed harmonization.
        """)

    with st.expander("Where does the model make larger errors?", expanded=True):
        st.markdown("""
        - **Intraday Error Profile:** MAE is lowest during nocturnal hours (00:00–04:00: MAE $\approx 45$ to $70$ veh/hr). MAE peaks during evening rush hours (16:00–17:00: MAE $\approx 220$ veh/hr), which is proportional to high baseline traffic volumes (> 5,500 veh/hr).
        - **Sensor Dropouts:** When ATR Station 301 loses telemetry for more than 1 hour, `traffic_lag_1h` is unavailable (`NaN`). The model gracefully reverts to seasonal lags (`traffic_lag_24h` / `lag_168h`), maintaining robustness.
        """)

    with st.expander("Which features contribute most to predictions?", expanded=True):
        st.markdown(r"""
        - **Diurnal Harmonics (`hour_cos`):** Mean |SHAP| = **918.97 veh/hr**. Represents the primary 24-hour day/night cycle.
        - **Short-Term Momentum (`traffic_lag_1h`):** Mean |SHAP| = **601.66 veh/hr**. Immediate prior state captures real-time persistence.
        - **Weekly Recurrence (`traffic_lag_168h`):** Mean |SHAP| = **190.75 veh/hr**. Aligns demand with the exact same hour of the preceding week.
        - **Rolling Boundaries (`traffic_roll_min_6h`):** Mean |SHAP| = **93.26 veh/hr**. Anchors recovery velocity from nocturnal lulls.
        """)


# -----------------------------------------------------------------------------
# 10. FOOTER
# -----------------------------------------------------------------------------
st.markdown("---")
st.markdown(
    '<div style="display: flex; justify-content: space-between; align-items: center; font-size: 0.76rem; color: #64748b; padding-bottom: 20px;">'
    '<div>URBAN MOBILITY &bull; TRAFFIC INTELLIGENCE PLATFORM &bull; PHASE 5</div>'
    '<div>MN DoT ATR 301 &bull; XGBoost Forecaster &bull; SQLite Relational Mart</div>'
    '</div>',
    unsafe_allow_html=True
)
