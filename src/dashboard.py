import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(page_title="Energy Demand Dashboard", page_icon="⚡", layout="wide")

# -------------------------------
# DATA PROCESSING FUNCTIONS
# -------------------------------
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
    if pd.isna(x) or x == 0:
        return "0"
    exponent = int(np.floor(np.log10(abs(x))))
    base = x / (10 ** exponent)
    return f"{base:.2f} × 10^{exponent}"

@st.cache_data
def load_processed_data():
    tz_dir = "../data_processed/timezone"
    resp_dir = "../data_processed/respondent"

    tz_frames = []
    resp_frames = []

    if os.path.exists(tz_dir):
        for f in os.listdir(tz_dir):
            if f.endswith(".csv"):
                df = pd.read_csv(os.path.join(tz_dir, f))
                df = clean_timeseries(df)
                df["Region"] = f.replace(".csv", "")
                df["Date"] = pd.to_datetime(df["period"])
                df["Demand_MW"] = df["value"]
                tz_frames.append(df)

    if os.path.exists(resp_dir):
        for f in os.listdir(resp_dir):
            if f.endswith(".csv"):
                df = pd.read_csv(os.path.join(resp_dir, f))
                df = clean_timeseries(df)
                df["Company"] = f.replace(".csv", "")
                df["Date"] = pd.to_datetime(df["period"])
                df["Demand_MW"] = df["value"]
                resp_frames.append(df)

    tz_df = pd.concat(tz_frames) if tz_frames else pd.DataFrame(columns=["Date", "Region", "Demand_MW"])
    resp_df = pd.concat(resp_frames) if resp_frames else pd.DataFrame(columns=["Date", "Company", "Demand_MW"])

    return tz_df, resp_df

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

def compute_indicators(df):
    df = df.sort_values("Date").copy()

    df["rolling_mean_7"] = df["Demand_MW"].rolling(7).mean()
    df["rolling_mean_30"] = df["Demand_MW"].rolling(30).mean()
    df["rolling_std_7"] = df["Demand_MW"].rolling(7).std()

    df["daily_growth"] = df["Demand_MW"].pct_change() * 100
    df["weekly_growth"] = df["Demand_MW"].pct_change(7) * 100

    df["diff_1"] = df["Demand_MW"].diff()
    df["diff_7"] = df["Demand_MW"].diff(7)

    return df

# -------------------------------
# MAIN APP
# -------------------------------
def main():
    st.title("⚡ Energy Demand Tracker")
    st.markdown("Monitoring electricity demand using the EIA dataset.")

    with st.spinner("Loading dataset..."):
        tz_df, resp_df = load_processed_data()

    if resp_df.empty or tz_df.empty:
        st.error("No data found! Please check your file paths.")
        return

    # --------------------------
    # SIDEBAR FILTERS
    # --------------------------
    st.sidebar.header("Filters")

    min_date = resp_df["Date"].min()
    max_date = resp_df["Date"].max()
    date_range = st.sidebar.date_input("Date Range", [min_date, max_date], min_value=min_date, max_value=max_date)

    if len(date_range) == 2:
        start_date, end_date = date_range
        tz_df = tz_df[(tz_df["Date"] >= pd.to_datetime(start_date)) & (tz_df["Date"] <= pd.to_datetime(end_date))]
        resp_df = resp_df[(resp_df["Date"] >= pd.to_datetime(start_date)) & (resp_df["Date"] <= pd.to_datetime(end_date))]

    regions = tz_df["Region"].unique()
    selected_regions = st.sidebar.multiselect("Timezone", regions, default=regions)
    tz_df = tz_df[tz_df["Region"].isin(selected_regions)]

    companies = resp_df["Company"].unique()
    selected_companies = st.sidebar.multiselect("Respondent", companies, default=companies)
    resp_df = resp_df[resp_df["Company"].isin(selected_companies)]

    time_group = st.sidebar.selectbox("Aggregation Level", ["Daily", "Weekly", "Monthly", "Yearly"])

    # --------------------------
    # KPI METRICS
    # --------------------------
    st.subheader("Key Statistics")
    col1, col2, col3, col4 = st.columns(4)

    total_demand = resp_df["Demand_MW"].sum()
    peak_demand = resp_df["Demand_MW"].max()
    avg_daily = resp_df.groupby("Date")["Demand_MW"].sum().mean()

    # FIX: Using .iloc[0] to avoid Series error on duplicate index
    peak_row = resp_df.sort_values("Demand_MW", ascending=False).iloc[0]
    peak_date = pd.to_datetime(peak_row["Date"]).strftime("%Y-%m-%d")

    col1.metric("Total Demand", f"{format_scientific(total_demand)} MW")
    col2.metric("Avg Daily Demand", f"{format_scientific(avg_daily)} MW")
    col3.metric("Peak Demand", f"{format_scientific(peak_demand)} MW")
    col4.metric("Peak Demand Date", peak_date)

    st.subheader("Trend Indicators")
    daily_series = resp_df.groupby("Date")["Demand_MW"].sum()
    latest_growth = daily_series.pct_change().iloc[-1] * 100
    weekly_growth = daily_series.pct_change(7).iloc[-1] * 100
    volatility = daily_series.rolling(7).std().iloc[-1]

    col5, col6, col7 = st.columns(3)
    col5.metric("Daily Growth", f"{latest_growth:.2f}%" if pd.notna(latest_growth) else "N/A")
    col6.metric("Weekly Growth", f"{weekly_growth:.2f}%" if pd.notna(weekly_growth) else "N/A")
    col7.metric("Volatility (7d)", f"{volatility:.2f}" if pd.notna(volatility) else "N/A")

    st.divider()

    # --------------------------
    # TABS FOR CLEANER UI
    # --------------------------
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📈 Overview", "🌍 Regional Analysis", "🏢 Company Analysis", "📊 Growth & Smoothing", "💾 Data Export"
    ])

    # ---- TAB 1: OVERVIEW ----
    with tab1:
        st.subheader("Aggregate Demand Over Time")
        window = st.slider("Rolling Window (days)", min_value=1, max_value=7, value=1)
        
        data = aggregate_time(resp_df.copy(), time_group)
        data["Demand_MW"] = data["Demand_MW"].rolling(window).mean()
        
        fig1 = px.line(data, x="Date", y="Demand_MW", template="plotly_dark", color_discrete_sequence=["#00E5FF"])
        fig1.update_traces(fill='tozeroy', fillcolor="rgba(0, 229, 255, 0.1)")
        fig1.update_layout(xaxis_title="Date", yaxis_title="Demand (MW)", hovermode="x unified")
        st.plotly_chart(fig1, use_container_width=True)

    # ---- TAB 2: REGIONAL ----
    with tab2:
        st.subheader("Demand by Region")
        
        # Plotly natively handles wide ranges elegantly, eliminating the need for strict visual offsets
        region_demand = tz_df.groupby("Region")["Demand_MW"].sum().reset_index().sort_values("Demand_MW")
        
        fig2 = px.bar(
            region_demand, x="Demand_MW", y="Region", orientation="h",
            template="plotly_dark", color_discrete_sequence=["#FF4081"],
            text_auto=".2s"
        )
        
        # Calculate dynamic x-axis range similar to your offset logic to highlight differences
        min_val = region_demand["Demand_MW"].min()
        std_val = region_demand["Demand_MW"].std()
        fig2.update_layout(xaxis=dict(range=[max(0, min_val - std_val), region_demand["Demand_MW"].max() * 1.1]))
        
        fig2.update_traces(textposition="outside")
        st.plotly_chart(fig2, use_container_width=True)

    # ---- TAB 3: COMPANY ----
    with tab3:
        col_chart3, col_chart4 = st.columns([2, 1])

        with col_chart3:
            st.subheader("Demand Contribution by Major Respondents")
            pivot_df = resp_df.pivot_table(index="Date", columns="Company", values="Demand_MW", aggfunc="sum").fillna(0)
            totals = pivot_df.sum().sort_values(ascending=False)
            top_companies = totals.head(8).index
            
            top_df = pivot_df[top_companies].copy()
            top_df["Others"] = pivot_df.drop(columns=top_companies).sum(axis=1)
            top_df = top_df.reset_index()
            
            fig3 = px.area(
                top_df, x="Date", y=top_df.columns[1:], 
                template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig3.update_layout(yaxis_title="Demand (MW)", legend_title="Company", hovermode="x unified")
            st.plotly_chart(fig3, use_container_width=True)

        with col_chart4:
            st.subheader("Market Share")
            company_shares = resp_df.groupby("Company")["Demand_MW"].sum().sort_values(ascending=False)
            top_shares = company_shares.head(8)
            others = company_shares.iloc[8:].sum()
            
            if others > 0:
                top_shares["Others"] = others
                
            fig4 = px.pie(
                names=top_shares.index, values=top_shares.values, hole=0.65,
                template="plotly_dark", color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig4.update_traces(textposition='inside', textinfo='percent+label')
            fig4.update_layout(showlegend=False)
            st.plotly_chart(fig4, use_container_width=True)

    # ---- TAB 4: GROWTH & SMOOTHING ----
    with tab4:
        col_chart5, col_chart6 = st.columns(2)
        
        with col_chart5:
            st.subheader("Growth Trends")
            growth_df = compute_indicators(aggregate_time(resp_df.copy(), time_group))
            
            # Using Plotly for multiple lines
            fig5 = px.line(
                growth_df, x="Date", y=["daily_growth", "weekly_growth"],
                template="plotly_dark",
                labels={"value": "Growth (%)", "variable": "Metric"}
            )
            fig5.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
            fig5.update_layout(hovermode="x unified")
            st.plotly_chart(fig5, use_container_width=True)

        with col_chart6:
            st.subheader("Trend with Smoothing")
            trend_df = compute_indicators(aggregate_time(resp_df.copy(), time_group))
            
            fig6 = px.line(
                trend_df, x="Date", y=["Demand_MW", "rolling_mean_7", "rolling_mean_30"],
                template="plotly_dark",
                labels={"value": "Demand (MW)", "variable": "Metric"},
                color_discrete_sequence=["rgba(255,255,255,0.3)", "#00E5FF", "#FF4081"]
            )
            fig6.update_layout(hovermode="x unified")
            st.plotly_chart(fig6, use_container_width=True)

    # ---- TAB 5: DATA EXPORT ----
    with tab5:
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

if __name__ == "__main__":
    main()