import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Energy Demand Dashboard", page_icon="⚡", layout="wide")

# -------------------------------
# 1. DATA PROCESSING FUNCTIONS
# -------------------------------
def clean_timeseries(df):
    df['period'] = pd.to_datetime(df['period'])
    df = df.sort_values("period")

    full_range = pd.date_range(start=df["period"].min(), end=df["period"].max(), freq="D")
    df = df.set_index("period").reindex(full_range).reset_index().rename(columns={"index": "period"})

    # --- Missing BEFORE ---
    missing_mask = df["value"].isna()
    missing_dates = df.loc[missing_mask, "period"].dt.strftime("%Y-%m-%d").tolist()
    missing_before = len(missing_dates)

    # --- Outliers ---
    z = (df["value"] - df["value"].mean()) / df["value"].std()
    outlier_mask = abs(z) > 4
    outlier_dates = df.loc[outlier_mask, "period"].dt.strftime("%Y-%m-%d").tolist()
    outliers = len(outlier_dates)

    df.loc[outlier_mask, "value"] = np.nan

    # --- Interpolation ---
    df["value"] = df["value"].interpolate()

    missing_after = df["value"].isna().sum()

    stats = {
        "missing_before": int(missing_before),
        "outliers_removed": int(outliers),
        "missing_after": int(missing_after),
        "missing_dates": missing_dates,
        "outlier_dates": outlier_dates
    }

    return df, stats

def format_power(x):
    if pd.isna(x) or x == 0:
        return "0 MW"
    abs_x = abs(x)
    if abs_x >= 1e9:
        return f"{x / 1e9:.2f} PW"  # Petawatts
    elif abs_x >= 1e6:
        return f"{x / 1e6:.2f} TW"  # Terawatts
    elif abs_x >= 1e3:
        return f"{x / 1e3:.2f} GW"  # Gigawatts
    else:
        return f"{x:,.0f} MW"       # Megawatts

@st.cache_data

def clean_timeseries(df):

    df['period'] = pd.to_datetime(df['period'])
    df = df.sort_values("period")

    full_range = pd.date_range(
        start=df["period"].min(),
        end=df["period"].max(),
        freq="D"
    )

    df = df.set_index("period").reindex(full_range)
    df.index.name = "period"
    df = df.reset_index()

    # outlier removal
    z = (df["value"] - df["value"].mean()) / df["value"].std()
    df.loc[abs(z) > 4, "value"] = np.nan

    # interpolation
    df["value"] = df["value"].interpolate()

    return df

def format_scientific(x):
    if x == 0:
        return "0"
    exponent = int(np.floor(np.log10(abs(x))))
    base = x / (10 ** exponent)
    return f"{base:.2f} × 10^{exponent}"

def load_processed_data():
    tz_dir = "../data_processed/timezone"
    resp_dir = "../data_processed/respondent"
    tz_frames, resp_frames = [], []
    tz_stats, resp_stats = [], []

    if os.path.exists(tz_dir):
        for f in os.listdir(tz_dir):
            if f.endswith(".csv"):
                df = pd.read_csv(os.path.join(tz_dir, f))
                df, stats = clean_timeseries(df)
                df["Region"] = f.replace(".csv", "")
                df["Date"] = pd.to_datetime(df["period"])
                df["Demand_MW"] = df["value"]
                tz_frames.append(df)
                stats['Region'] = f.replace(".csv", "")
                tz_stats.append(stats)

    if os.path.exists(resp_dir):
        for f in os.listdir(resp_dir):
            if f.endswith(".csv"):
                df = pd.read_csv(os.path.join(resp_dir, f))
                df, stats = clean_timeseries(df)
                df["Company"] = f.replace(".csv", "")
                df["Date"] = pd.to_datetime(df["period"])
                df["Demand_MW"] = df["value"]
                resp_frames.append(df)
                stats['Company'] = f.replace(".csv", "")
                resp_stats.append(stats)

    tz_df = pd.concat(tz_frames) if tz_frames else pd.DataFrame(columns=["Date", "Region", "Demand_MW"])
    resp_df = pd.concat(resp_frames) if resp_frames else pd.DataFrame(columns=["Date", "Company", "Demand_MW"])
    return tz_df, resp_df,  pd.DataFrame(tz_stats), pd.DataFrame(resp_stats)

def aggregate_time(df, level):
    if level == "Daily":
        return df.groupby("Date")["Demand_MW"].sum().reset_index()
    if level == "Weekly":
        df["Week"] = df["Date"].dt.to_period("W").apply(lambda r: r.start_time)
        return df.groupby("Week")["Demand_MW"].sum().reset_index().rename(columns={"Week": "Date"})
    if level == "Monthly":
        df["Month"] = df["Date"].dt.to_period("M").apply(lambda r: r.start_time)
        return df.groupby("Month")["Demand_MW"].sum().reset_index().rename(columns={"Month": "Date"})
    if level == "Yearly":
        df["Year"] = df["Date"].dt.to_period("Y").apply(lambda r: r.start_time)
        return df.groupby("Year")["Demand_MW"].sum().reset_index().rename(columns={"Year": "Date"})

def compute_daily_physics(df):
    """Computes anomalies, YTD, and ramps strictly on daily data"""
    df = df.sort_values("Date").copy()
    
    # 30-day rolling for anomalies
    df["rolling_mean_30"] = df["Demand_MW"].rolling(30, min_periods=1).mean()
    df["rolling_std_30"] = df["Demand_MW"].rolling(30, min_periods=1).std()
    
    df["z_score"] = (df["Demand_MW"] - df["rolling_mean_30"]) / df["rolling_std_30"].replace(0, np.nan)
    df["is_anomaly"] = abs(df["z_score"]) > 3
    
    df["ramp_rate"] = df["Demand_MW"].diff()
    df['Year'] = df['Date'].dt.year
    df['DayOfYear'] = df['Date'].dt.dayofyear
    df['Cumulative_Demand'] = df.groupby('Year')['Demand_MW'].cumsum()
    return df

# -------------------------------
# 2. MAIN APP & SIDEBAR
# -------------------------------
def main():
    st.title("⚡ Advanced Energy Grid Analytics")
    st.markdown("Comprehensive tracking, forecasting, and grid stress diagnostics.")

    with st.spinner("Loading and analyzing grid data..."):
        tz_df, resp_df, tz_stats, resp_stats = load_processed_data()

    if resp_df.empty or tz_df.empty:
        st.error("No data found! Please check your file paths.")
        return

    # ---- SIDEBAR FILTERS ----
    st.sidebar.header("Filters & Controls")

    # NEW: The Perspective Toggle. This decides which dataset drives the main dashboard
    analysis_mode = st.sidebar.radio(
        "Primary Analysis Mode", 
        ["Respondent (Company View)", "Timezone (Region View)"],
        help="Select which dataset drives the Main KPIs, Overviews, and Anomalies."
    )

    min_date, max_date = resp_df["Date"].min(), resp_df["Date"].max()
    date_range = st.sidebar.date_input("Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

    if len(date_range) == 2:
        start_date, end_date = date_range
        tz_df = tz_df[(tz_df["Date"] >= pd.to_datetime(start_date)) & (tz_df["Date"] <= pd.to_datetime(end_date))]
        resp_df = resp_df[(resp_df["Date"] >= pd.to_datetime(start_date)) & (resp_df["Date"] <= pd.to_datetime(end_date))]

    selected_regions = st.sidebar.multiselect("Filter Regions", tz_df["Region"].unique(), default=tz_df["Region"].unique())
    tz_df = tz_df[tz_df["Region"].isin(selected_regions)]

    selected_companies = st.sidebar.multiselect("Filter Respondents", resp_df["Company"].unique(), default=resp_df["Company"].unique())
    resp_df = resp_df[resp_df["Company"].isin(selected_companies)]

    time_group = st.sidebar.selectbox("Trend Aggregation Level", ["Daily", "Weekly", "Monthly", "Yearly"])

    # -------------------------------
    # 3. DYNAMIC DATA ROUTING
    # -------------------------------
    # Set the master dataframe based on user's selected mode so filters actually work
    master_df = resp_df.copy() if "Respondent" in analysis_mode else tz_df.copy()

    # Apply aggregations to the selected master dataset
    agg_data = aggregate_time(master_df, time_group)
    agg_data = agg_data.sort_values("Date")
    agg_data["Period_Growth_%"] = agg_data["Demand_MW"].pct_change() * 100 # Growth now respects Weekly/Monthly!

    daily_agg = master_df.groupby("Date")["Demand_MW"].sum().reset_index()
    daily_agg = compute_daily_physics(daily_agg)

    # -------------------------------
    # 4. KPI METRICS
    # -------------------------------
    st.subheader(f"Grid Status Indicators ({analysis_mode.split(' ')[0]} Data)")
    col1, col2, col3, col4, col5 = st.columns(5)

    total_demand = daily_agg["Demand_MW"].sum()
    avg_daily = daily_agg["Demand_MW"].mean()
    
    if not daily_agg.empty:
        peak_row = daily_agg.sort_values("Demand_MW", ascending=False).iloc[0]
        peak_date = pd.to_datetime(peak_row["Date"]).strftime("%Y-%m-%d")
        latest_growth = agg_data["Period_Growth_%"].iloc[-1]
        total_anomalies = daily_agg["is_anomaly"].sum()
    else:
        peak_row = {"Demand_MW": 0}
        latest_growth = np.nan
        total_anomalies = 0

    col1.metric("Total Demand", format_power(total_demand))
    col2.metric("Avg Daily Load", format_power(avg_daily))
    col3.metric("Peak Demand", format_power(peak_row['Demand_MW']))
    col4.metric(f"Latest Growth ({time_group})", f"{latest_growth:.2f}%" if pd.notna(latest_growth) else "N/A")
    col5.metric("Anomalies Detected", f"{total_anomalies} Days")

    st.divider()

    # -------------------------------
    # 5. TABBED DASHBOARD
    # -------------------------------
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📈 Trends & Growth", "📅 Seasonality & YTD", "🌍 Deep Dive: Regions", 
        "🏢 Deep Dive: Companies", "⚡ Grid Physics & Anomalies", "💾 Data Export"
    ])

    # ---- TAB 1: TRENDS & GROWTH ----
    with tab1:
        st.subheader(f"Aggregate Demand ({time_group})")
        window = st.slider("Smoothing Window (Moving Average)", min_value=1, max_value=30, value=7)
        
        plot_data = agg_data.copy()
        plot_data["Smoothed_Demand"] = plot_data["Demand_MW"].rolling(window, min_periods=1).mean()
        
        fig1 = px.line(plot_data, x="Date", y=["Demand_MW", "Smoothed_Demand"], template="plotly_dark",
                       color_discrete_sequence=["rgba(0, 229, 255, 0.3)", "#FF4081"],
                       labels={"value": "Demand (MW)", "variable": "Metric"})
        fig1.update_layout(hovermode="x unified", legend_title="")
        st.plotly_chart(fig1, use_container_width=True)

        col_trend1, col_trend2 = st.columns(2)
        with col_trend1:
            st.subheader(f"Growth Trends ({time_group})")
            fig_growth = px.bar(agg_data, x="Date", y="Period_Growth_%", template="plotly_dark",
                                 color="Period_Growth_%", color_continuous_scale="RdBu_r")
            fig_growth.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
            st.plotly_chart(fig_growth, use_container_width=True)

        with col_trend2:
            st.subheader("Average Demand by Day of Week")
            dow_df = daily_agg.copy()
            dow_df['DayOfWeek'] = dow_df['Date'].dt.day_name()
            dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            dow_demand = dow_df.groupby('DayOfWeek')['Demand_MW'].mean().reindex(dow_order).reset_index()
            
            fig_dow = px.bar(dow_demand, x="DayOfWeek", y="Demand_MW", template="plotly_dark", 
                             color_discrete_sequence=["#B388FF"], text_auto=".2s")
            st.plotly_chart(fig_dow, use_container_width=True)

    # ---- TAB 2: SEASONALITY & YTD ----
    with tab2:
        col_seas1, col_seas2 = st.columns(2)
        
        with col_seas1:
            st.subheader("Cumulative YTD Trajectory")
            daily_agg['Year_Str'] = daily_agg['Year'].astype(str)
            fig_ytd = px.line(daily_agg, x="DayOfYear", y="Cumulative_Demand", color="Year_Str", 
                              template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_ytd.update_layout(xaxis_title="Day of Year", yaxis_title="Total MW Consumed")
            st.plotly_chart(fig_ytd, use_container_width=True)

        with col_seas2:
            st.subheader("Year-over-Year (YoY) Overlay")
            yoy_df = daily_agg.copy()
            yoy_df['DummyDate'] = yoy_df['Date'].apply(lambda d: d.replace(year=2024))
            fig_yoy = px.line(yoy_df, x="DummyDate", y="Demand_MW", color="Year_Str", 
                              template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Set2)
            fig_yoy.update_layout(xaxis_tickformat="%b %d", xaxis_title="Time of Year", yaxis_title="Daily Demand (MW)")
            st.plotly_chart(fig_yoy, use_container_width=True)

        st.divider()
        st.subheader("Seasonal Heatmap (Usage Patterns)")
        heat_df = daily_agg.copy()
        heat_df['Month'] = heat_df['Date'].dt.month_name()
        heat_df['DOW'] = heat_df['Date'].dt.day_name()
        
        month_order = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        dow_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        fig_heat = px.density_heatmap(heat_df, x="Month", y="DOW", z="Demand_MW", histfunc="avg",
                                      template="plotly_dark", color_continuous_scale="Viridis",
                                      category_orders={"Month": month_order, "DOW": dow_order[::-1]})
        st.plotly_chart(fig_heat, use_container_width=True)

    # ---- TAB 3: REGIONAL MATRIX ----
    with tab3:
        st.subheader("Total Demand by Region")
        region_demand = tz_df.groupby("Region")["Demand_MW"].sum().reset_index().sort_values("Demand_MW")
        fig_reg_bar = px.bar(region_demand, x="Demand_MW", y="Region", orientation="h", template="plotly_dark", 
                             color_discrete_sequence=["#FF4081"], text_auto=".2s")
        st.plotly_chart(fig_reg_bar, use_container_width=True)

        col_reg1, col_reg2 = st.columns(2)
        with col_reg1:
            st.subheader("Regional Volatility (Box Plot)")
            fig_box_reg = px.box(tz_df, x="Region", y="Demand_MW", color="Region", template="plotly_dark")
            fig_box_reg.update_layout(showlegend=False)
            st.plotly_chart(fig_box_reg, use_container_width=True)

        with col_reg2:
            st.subheader("Grid Stress (Regional Correlation)")
            pivot_tz = tz_df.pivot_table(index="Date", columns="Region", values="Demand_MW", aggfunc="sum")
            fig_corr = px.imshow(pivot_tz.corr(), text_auto=".2f", aspect="auto", template="plotly_dark", color_continuous_scale="RdBu_r")
            st.plotly_chart(fig_corr, use_container_width=True)

    # ---- TAB 4: COMPANY / MARKET SHARE ----
    with tab4:
        col_comp1, col_comp2 = st.columns([2, 1])

        with col_comp1:
            st.subheader("Demand Contribution by Top Respondents")
            pivot_resp = resp_df.pivot_table(index="Date", columns="Company", values="Demand_MW", aggfunc="sum").fillna(0)
            if not pivot_resp.empty:
                top_companies = pivot_resp.sum().sort_values(ascending=False).head(8).index
                top_df = pivot_resp[top_companies].copy()
                top_df["Others"] = pivot_resp.drop(columns=top_companies, errors='ignore').sum(axis=1)
                top_df = top_df.reset_index()
                
                fig_area = px.area(top_df, x="Date", y=top_df.columns[1:], template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_area.update_layout(yaxis_title="Demand (MW)", hovermode="x unified")
                st.plotly_chart(fig_area, use_container_width=True)

        with col_comp2:
            st.subheader("Market Share")
            company_shares = resp_df.groupby("Company")["Demand_MW"].sum().sort_values(ascending=False)
            if not company_shares.empty:
                top_shares = company_shares.head(8)
                others = company_shares.iloc[8:].sum()
                if others > 0: top_shares["Others"] = others
                    
                fig_pie = px.pie(names=top_shares.index, values=top_shares.values, hole=0.65, template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(showlegend=False)
                st.plotly_chart(fig_pie, use_container_width=True)
            
        st.subheader("Company Volatility")
        if not pivot_resp.empty:
            top_resp_df = resp_df[resp_df["Company"].isin(top_companies)]
            fig_box_comp = px.box(top_resp_df, x="Company", y="Demand_MW", color="Company", template="plotly_dark")
            fig_box_comp.update_layout(showlegend=False)
            st.plotly_chart(fig_box_comp, use_container_width=True)

    # ---- TAB 5: GRID PHYSICS & ANOMALIES ----
    with tab5:
        st.subheader(f"Automated Anomaly Detection ({analysis_mode.split(' ')[0]} Data)")
        fig_anom = go.Figure()
        fig_anom.add_trace(go.Scatter(x=daily_agg["Date"], y=daily_agg["Demand_MW"], name="Standard Demand", line=dict(color="#00E5FF")))
        
        anomalies = daily_agg[daily_agg["is_anomaly"]]
        fig_anom.add_trace(go.Scatter(x=anomalies["Date"], y=anomalies["Demand_MW"], mode="markers", 
                                     name="Anomaly (>3 Std Dev)", marker=dict(color="red", size=8)))
        fig_anom.update_layout(template="plotly_dark", hovermode="x unified")
        st.plotly_chart(fig_anom, use_container_width=True)

        col_phys1, col_phys2 = st.columns(2)
        with col_phys1:
            st.subheader("Load Duration Curve (LDC)")
            st.caption("Percentage of time demand exceeds a given level.")
            ldc_data = daily_agg["Demand_MW"].sort_values(ascending=False).values
            if len(ldc_data) > 0:
                ldc_p = np.linspace(0, 100, len(ldc_data))
                fig_ldc = px.line(x=ldc_p, y=ldc_data, template="plotly_dark", color_discrete_sequence=["#FF4081"], labels={"x": "% of Time", "y": "Demand (MW)"})
                fig_ldc.add_hline(y=ldc_data.min(), line_dash="dash", annotation_text="Base Load")
                st.plotly_chart(fig_ldc, use_container_width=True)

        with col_phys2:
            st.subheader("Day-to-Day Ramp Rates")
            st.caption("Absolute change in demand from the previous day.")
            fig_ramp = px.bar(daily_agg, x="Date", y="ramp_rate", template="plotly_dark", color="ramp_rate", color_continuous_scale="RdBu_r")
            fig_ramp.update_layout(yaxis_title="MW Change vs Previous Day")
            st.plotly_chart(fig_ramp, use_container_width=True)

    # ---- TAB 6: DATA EXPORT ----
    with tab6:
        st.subheader("Raw Data Export")
        st.write("Download the filtered dataset based on your sidebar selections.")
        
        col_data1, col_data2 = st.columns(2)
        with col_data1:
            st.dataframe(resp_df.head(100), use_container_width=True)
            csv_resp = resp_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Respondent Data (CSV)", data=csv_resp, file_name="filtered_respondent_data.csv", mime="text/csv")
            
        with col_data2:
            st.dataframe(tz_df.head(100), use_container_width=True)
            csv_tz = tz_df.to_csv(index=False).encode('utf-8')
            st.download_button("Download Timezone Data (CSV)", data=csv_tz, file_name="filtered_timezone_data.csv", mime="text/csv")

        st.subheader("Data Quality Report")

        col_q1, col_q2, col_q3 = st.columns(3)

        col_q1.metric("Missing Values (Before)", int(resp_stats["missing_before"].sum()))
        col_q2.metric("Outliers Removed", int(resp_stats["outliers_removed"].sum()))
        col_q3.metric("Remaining Missing", int(resp_stats["missing_after"].sum()))

        with st.expander("Detailed Respondent Data Quality"):
            st.dataframe(resp_stats.drop(columns=["missing_dates", "outlier_dates"], errors="ignore"),width="stretch")

            selected_company = st.selectbox(
                "Select Company to View Affected Dates",
                resp_stats["Company"]
            )

            row = resp_stats[resp_stats["Company"] == selected_company].iloc[0]

            st.write("**Missing Dates:**")
            st.write(row["missing_dates"] if row["missing_dates"] else "None")

            st.write("**Outlier Dates:**")
            st.write(row["outlier_dates"] if row["outlier_dates"] else "None")

        with st.expander("Detailed Region Data Quality"):
            st.dataframe(tz_stats.drop(columns=["missing_dates", "outlier_dates"], errors="ignore"),width="stretch")

            selected_region = st.selectbox(
                "Select Region to View Affected Dates",
                tz_stats["Region"]
            )

            row = tz_stats[tz_stats["Region"] == selected_region].iloc[0]

            st.write("**Missing Dates:**")
            st.write(row["missing_dates"] if row["missing_dates"] else "None")

            st.write("**Outlier Dates:**")
            st.write(row["outlier_dates"] if row["outlier_dates"] else "None")

        resp_stats_export = resp_stats.copy()
        resp_stats_export["missing_dates"] = resp_stats_export["missing_dates"].apply(lambda x: ",".join(x))
        resp_stats_export["outlier_dates"] = resp_stats_export["outlier_dates"].apply(lambda x: ",".join(x))
        quality_csv = resp_stats_export.to_csv(index=False).encode('utf-8')

        st.download_button(
            "Download Data Quality Report (Respondent)",
            data=quality_csv,
            file_name="data_quality_respondent.csv",
            mime="text/csv"
        )
        tz_stats_export = tz_stats.copy()
        tz_stats_export["missing_dates"] = tz_stats_export["missing_dates"].apply(lambda x: ",".join(x))
        tz_stats_export["outlier_dates"] = tz_stats_export["outlier_dates"].apply(lambda x: ",".join(x))
        quality_csv_tz = tz_stats_export.to_csv(index=False).encode('utf-8')

        st.download_button(
            "Download Data Quality Report (Region)",
            data=quality_csv_tz,
            file_name="data_quality_region.csv",
            mime="text/csv"
        )


if __name__ == "__main__":
    main()