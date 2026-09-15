"""
Generate Comprehensive EDA Figures
Urban Mobility & Traffic Intelligence - Phase 2

Generates 12 publication-ready analytical charts based on the processed dataset
and saves them to reports/figures/.
"""

import os
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

# Set styling
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
plt.rcParams['figure.dpi'] = 150

PROCESSED_PATH = os.path.join("data", "processed", "traffic_cleaned.csv")
FIG_DIR = os.path.join("reports", "figures")
os.makedirs(FIG_DIR, exist_ok=True)


def generate_all_figures():
    print("[EDA] Loading processed dataset...")
    df = pd.read_csv(PROCESSED_PATH)
    df['date_time'] = pd.to_datetime(df['date_time'])
    
    # 1. Traffic Volume Distribution
    print("[EDA] Generating Figure 1: Traffic Volume Distribution...")
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.histplot(df['traffic_volume'], kde=True, bins=50, color='#1f77b4', ax=ax)
    ax.set_title('Distribution of Interstate Hourly Traffic Volume (Bimodal Structure)', fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel('Traffic Volume (Vehicles / Hour)', fontsize=11)
    ax.set_ylabel('Frequency / Count', fontsize=11)
    ax.axvline(df['traffic_volume'].mean(), color='red', linestyle='--', linewidth=1.5, label=f'Mean: {df["traffic_volume"].mean():.1f}')
    ax.axvline(df['traffic_volume'].median(), color='green', linestyle=':', linewidth=1.5, label=f'Median: {df["traffic_volume"].median():.1f}')
    ax.legend(fontsize=10)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, '01_traffic_volume_distribution.png'))
    plt.close(fig)

    # 2. Traffic Volume by Hour
    print("[EDA] Generating Figure 2: Traffic Volume by Hour...")
    fig, ax = plt.subplots(figsize=(10, 5))
    hourly_stats = df.groupby('hour')['traffic_volume'].agg(['mean', 'std']).reset_index()
    ax.plot(hourly_stats['hour'], hourly_stats['mean'], color='#005f73', marker='o', linewidth=2.5, label='Mean Volume')
    ax.fill_between(hourly_stats['hour'], hourly_stats['mean'] - hourly_stats['std'], hourly_stats['mean'] + hourly_stats['std'], color='#94d2bd', alpha=0.3, label='±1 Std Dev')
    ax.set_title('Diurnal Traffic Profile Across 24-Hour Cycle', fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel('Hour of Day (0 - 23)', fontsize=11)
    ax.set_ylabel('Average Traffic Volume', fontsize=11)
    ax.set_xticks(range(0, 24))
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(fontsize=10)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, '02_traffic_volume_by_hour.png'))
    plt.close(fig)

    # 3. Traffic Volume by Day of Week
    print("[EDA] Generating Figure 3: Traffic Volume by Day of Week...")
    fig, ax = plt.subplots(figsize=(9, 5))
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_stats = df.groupby('day_name')['traffic_volume'].mean().reindex(day_order)
    colors = ['#0a9396' if d not in ['Saturday', 'Sunday'] else '#ca6702' for d in day_order]
    bars = ax.bar(day_order, day_stats, color=colors, edgecolor='black', alpha=0.85)
    ax.set_title('Average Traffic Volume by Day of Week (Weekday vs Weekend Shift)', fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel('Day of Week', fontsize=11)
    ax.set_ylabel('Average Volume (Vehicles / Hour)', fontsize=11)
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.0f}', xy=(bar.get_x() + bar.get_width() / 2, height), xytext=(0, 3),
                    textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, '03_traffic_volume_by_day_of_week.png'))
    plt.close(fig)

    # 4. Traffic Volume by Month
    print("[EDA] Generating Figure 4: Traffic Volume by Month...")
    fig, ax = plt.subplots(figsize=(11, 5))
    month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
    monthly_stats = df.groupby('month_name')['traffic_volume'].mean().reindex(month_order)
    ax.plot(month_order, monthly_stats, marker='s', color='#9b2226', linewidth=2.5, markersize=7)
    ax.set_title('Seasonal Traffic Volume Fluctuation by Month', fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel('Month', fontsize=11)
    ax.set_ylabel('Average Traffic Volume', fontsize=11)
    plt.xticks(rotation=30)
    for i, txt in enumerate(monthly_stats):
        ax.annotate(f'{txt:.0f}', (month_order[i], monthly_stats.iloc[i] + 20), ha='center', fontsize=9)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, '04_traffic_volume_by_month.png'))
    plt.close(fig)

    # 5. Traffic Volume by Year
    print("[EDA] Generating Figure 5: Traffic Volume by Year...")
    fig, ax = plt.subplots(figsize=(9, 5))
    yearly_stats = df.groupby('year')['traffic_volume'].agg(['mean', 'count']).reset_index()
    bars = ax.bar(yearly_stats['year'].astype(str), yearly_stats['mean'], color='#3a5a40', edgecolor='black', alpha=0.85)
    ax.set_title('Historical Annual Mean Traffic Volume (2012 - 2018)', fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel('Calendar Year', fontsize=11)
    ax.set_ylabel('Mean Hourly Traffic Volume', fontsize=11)
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.0f}', xy=(bar.get_x() + bar.get_width() / 2, height), xytext=(0, 3),
                    textcoords="offset points", ha='center', va='bottom', fontsize=9, fontweight='bold')
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, '05_traffic_volume_by_year.png'))
    plt.close(fig)

    # 6. Morning vs Evening Rush Hour Comparison
    print("[EDA] Generating Figure 6: Rush Hour Comparison...")
    fig, ax = plt.subplots(figsize=(10, 5))
    # Categorize hours
    conditions = [
        df['is_morning_rush_hour'] == 1,
        df['is_evening_rush_hour'] == 1,
        (df['is_weekend'] == 0) & (df['is_morning_rush_hour'] == 0) & (df['is_evening_rush_hour'] == 0),
        df['is_weekend'] == 1
    ]
    choices = ['Morning Rush (06-09)', 'Evening Rush (15-18)', 'Weekday Off-Peak', 'Weekend']
    df['period_type'] = np.select(conditions, choices, default='Other')
    
    sns.boxplot(data=df, x='period_type', y='traffic_volume', palette=['#2a9d8f', '#e76f51', '#457b9d', '#e9c46a'], ax=ax, order=choices)
    ax.set_title('Traffic Volume Distribution: Commuter Rush Hours vs. Off-Peak Periods', fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel('Commuter Period Classification', fontsize=11)
    ax.set_ylabel('Hourly Traffic Volume', fontsize=11)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, '06_rush_hour_comparison.png'))
    plt.close(fig)

    # 7. Weekday vs Weekend Hourly Profile
    print("[EDA] Generating Figure 7: Weekday vs Weekend Hourly Profile...")
    fig, ax = plt.subplots(figsize=(10, 5))
    ww = df.groupby(['hour', 'is_weekend'])['traffic_volume'].mean().unstack()
    ax.plot(ww.index, ww[0], color='#1d3557', marker='o', linewidth=2.5, label='Weekday (Mon-Fri)')
    ax.plot(ww.index, ww[1], color='#e63946', marker='s', linewidth=2.5, linestyle='--', label='Weekend (Sat-Sun)')
    ax.set_title('Hourly Diurnal Profile: Weekday Commuting vs Weekend Leisure', fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel('Hour of Day', fontsize=11)
    ax.set_ylabel('Average Volume (Vehicles / Hour)', fontsize=11)
    ax.set_xticks(range(0, 24))
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.legend(fontsize=11)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, '07_weekday_vs_weekend_hourly.png'))
    plt.close(fig)

    # 8. Traffic Trends Over Time (Weekly Resampled)
    print("[EDA] Generating Figure 8: Traffic Trend Over Time...")
    fig, ax = plt.subplots(figsize=(14, 5))
    weekly_ts = df.set_index('date_time')['traffic_volume'].resample('W').mean()
    rolling_30 = weekly_ts.rolling(4, min_periods=1).mean()
    ax.plot(weekly_ts.index, weekly_ts, color='#8ecae6', alpha=0.6, label='Weekly Average')
    ax.plot(rolling_30.index, rolling_30, color='#023047', linewidth=2, label='4-Week Moving Average')
    # Mark the 307-day blackout
    ax.axvspan(pd.to_datetime('2014-08-08'), pd.to_datetime('2015-06-11'), color='#ffb703', alpha=0.25, label='Historical Blackout Gap (307 Days)')
    ax.set_title('Longitudinal Traffic Volume Trend (2012 - 2018) with Major Data Gap Highlighted', fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel('Observation Date', fontsize=11)
    ax.set_ylabel('Mean Volume (Vehicles / Hour)', fontsize=11)
    ax.legend(fontsize=10, loc='lower left')
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, '08_traffic_trend_over_time.png'))
    plt.close(fig)

    # 9. Traffic Volume by Weather Main
    print("[EDA] Generating Figure 9: Traffic Volume by Weather Main...")
    fig, ax = plt.subplots(figsize=(10, 6))
    weather_stats = df.groupby('weather_main')['traffic_volume'].agg(['mean', 'count']).sort_values('mean')
    bars = ax.barh(weather_stats.index, weather_stats['mean'], color='#457b9d', edgecolor='black', alpha=0.85)
    ax.set_title('Mean Traffic Volume by Macro Meteorological Category', fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel('Mean Traffic Volume (Vehicles / Hour)', fontsize=11)
    ax.set_ylabel('Dominant Weather Category', fontsize=11)
    for bar in bars:
        width = bar.get_width()
        ax.annotate(f'{width:.0f}', xy=(width, bar.get_y() + bar.get_height() / 2), xytext=(5, 0),
                    textcoords="offset points", ha='left', va='center', fontsize=9, fontweight='bold')
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, '09_weather_impact_traffic.png'))
    plt.close(fig)

    # 10. Precipitation & Temperature vs Volume
    print("[EDA] Generating Figure 10: Weather vs Volume Relationships...")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    # Temp vs Volume (binned)
    df['temp_bin'] = pd.cut(df['temp_celsius'], bins=np.linspace(-30, 35, 14))
    temp_profile = df.groupby('temp_bin', observed=False)['traffic_volume'].mean()
    temp_bin_labels = [f'{int(b.left)} to {int(b.right)}°C' for b in temp_profile.index]
    ax1.bar(range(len(temp_profile)), temp_profile.values, color='#e76f51', edgecolor='black', alpha=0.8)
    ax1.set_xticks(range(len(temp_profile)))
    ax1.set_xticklabels(temp_bin_labels, rotation=45, ha='right', fontsize=8)
    ax1.set_title('Traffic Volume Across Temperature Bands', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Mean Volume', fontsize=10)
    ax1.set_xlabel('Ambient Temperature Band (°C)', fontsize=10)
    
    # Rain Impact
    rain_bins = [-0.1, 0.0, 2.5, 7.6, 60.0]
    rain_labels = ['No Rain (0)', 'Light (<2.5mm)', 'Moderate (2.5-7.6mm)', 'Heavy (>7.6mm)']
    df['rain_tier'] = pd.cut(df['rain_1h'], bins=rain_bins, labels=rain_labels)
    rain_profile = df.groupby('rain_tier', observed=False)['traffic_volume'].mean()
    ax2.bar(rain_labels, rain_profile.values, color='#264653', edgecolor='black', alpha=0.85)
    ax2.set_title('Traffic Volume by Rainfall Intensity Tier', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Mean Volume', fontsize=10)
    ax2.set_xlabel('Rainfall Intensity Tier', fontsize=10)
    for i, v in enumerate(rain_profile.values):
        ax2.annotate(f'{v:.0f}', (i, v + 25), ha='center', fontsize=9, fontweight='bold')
    
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, '10_precipitation_temperature_relationships.png'))
    plt.close(fig)

    # 11. Missing Data & Gap Analysis
    print("[EDA] Generating Figure 11: Missing Data and Timeline Gaps...")
    fig, ax = plt.subplots(figsize=(14, 4))
    full_idx = pd.date_range(start=df['date_time'].min(), end=df['date_time'].max(), freq='h')
    coverage_df = pd.DataFrame(index=full_idx)
    coverage_df['recorded'] = coverage_df.index.isin(df['date_time']).astype(int)
    monthly_coverage = coverage_df['recorded'].resample('M').mean() * 100
    
    ax.plot(monthly_coverage.index, monthly_coverage.values, color='#e63946', marker='o', linewidth=1.8, markersize=4)
    ax.fill_between(monthly_coverage.index, 0, monthly_coverage.values, color='#f1faee', alpha=0.5)
    ax.axhline(100, color='gray', linestyle=':', alpha=0.7)
    ax.set_title('Historical Monthly Observation Completeness Rate (% of Expected Hours Logged)', fontsize=13, fontweight='bold', pad=12)
    ax.set_ylabel('Completeness (%)', fontsize=10)
    ax.set_xlabel('Year / Month', fontsize=10)
    ax.set_ylim(-5, 105)
    ax.annotate('307-Day Sensor Blackout\n(Aug 2014 - Jun 2015: 0%)', xy=(pd.to_datetime('2014-12-01'), 5),
                xytext=(pd.to_datetime('2013-06-01'), 40),
                arrowprops=dict(facecolor='black', arrowstyle='->', lw=1.5),
                fontsize=9, fontweight='bold', bbox=dict(boxstyle='round,pad=0.3', facecolor='#ffe8d6', edgecolor='#ddbea9'))
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, '11_missing_data_gaps.png'))
    plt.close(fig)

    # 12. Peak vs Low Traffic Heatmap (Hour of Day vs Day of Week)
    print("[EDA] Generating Figure 12: Peak vs Low Traffic Heatmap...")
    fig, ax = plt.subplots(figsize=(12, 6))
    pivot = df.pivot_table(index='day_name', columns='hour', values='traffic_volume', aggfunc='mean').reindex(day_order)
    sns.heatmap(pivot, cmap='YlGnBu', annot=False, cbar_kws={'label': 'Mean Vehicles / Hour'}, ax=ax)
    ax.set_title('Interstate Traffic Intensity Heatmap: Hour of Day vs. Day of Week', fontsize=14, fontweight='bold', pad=12)
    ax.set_xlabel('Hour of Day (0 to 23)', fontsize=11)
    ax.set_ylabel('Day of Week', fontsize=11)
    plt.tight_layout()
    fig.savefig(os.path.join(FIG_DIR, '12_peak_vs_low_traffic_heatmap.png'))
    plt.close(fig)

    print(f"[EDA] Successfully generated all 12 figures in: {FIG_DIR}")


if __name__ == "__main__":
    generate_all_figures()
