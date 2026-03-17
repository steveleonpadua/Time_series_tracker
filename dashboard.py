import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os

# --- PAGE CONFIG ---
st.set_page_config(page_title="Energy Demand Dashboard", page_icon="⚡", layout="wide")


# --- DATA LOADING ---
@st.cache_data
def load_processed_data():

    tz_dir = "../data_processed/timezone"
    resp_dir = "../data_processed/respondent"

    tz_frames = []
    resp_frames = []

    # Load timezone files
    for f in os.listdir(tz_dir):

        df = pd.read_csv(os.path.join(tz_dir, f))

        df["Region"] = f.replace(".csv", "")
        df["Date"] = pd.to_datetime(df["period"])
        df["Demand_MW"] = df["value"]

        tz_frames.append(df)

    # Load respondent files
    for f in os.listdir(resp_dir):

        df = pd.read_csv(os.path.join(resp_dir, f))

        df["Company"] = f.replace(".csv", "")
        df["Date"] = pd.to_datetime(df["period"])
        df["Demand_MW"] = df["value"]

        resp_frames.append(df)

    tz_df = pd.concat(tz_frames)
    resp_df = pd.concat(resp_frames)

    df = resp_df.merge(
        tz_df[["Date", "Region"]],
        on="Date",
        how="left"
    )

    return df


# --- TIME AGGREGATION ---
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


# --- TREND PLOT ---
def plot_trend(df, title, time_group):

    plt.style.use("dark_background")

    fig, ax = plt.subplots(figsize=(10,4))

    data = aggregate_time(df, time_group)

    ax.plot(data["Date"], data["Demand_MW"], color="#00E5FF", linewidth=2)
    ax.fill_between(data["Date"], data["Demand_MW"], color="#00E5FF", alpha=0.1)

    ax.set_title(title, loc="left")
    ax.set_ylabel("Demand (MW)")
    ax.grid(axis="y", linestyle="--", alpha=0.3)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)

    plt.xticks(rotation=45)
    plt.tight_layout()

    return fig


# --- MAIN DASHBOARD ---
def main():

    st.title("⚡ Energy Demand Tracker")
    st.markdown("Monitoring electricity demand using the EIA dataset.")

    with st.spinner("Loading dataset..."):
        df = load_processed_data()

    # --- SIDEBAR ---
    st.sidebar.header("Filters")

    regions = df["Region"].dropna().unique()
    companies = df["Company"].dropna().unique()

    selected_regions = st.sidebar.multiselect(
        "Timezone",
        regions,
        default=regions
    )

    selected_companies = st.sidebar.multiselect(
        "Respondent",
        companies,
        default=companies
    )

    # Date range filter
    min_date = df["Date"].min()
    max_date = df["Date"].max()

    date_range = st.sidebar.date_input(
        "Date Range",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )

    # Aggregation level
    time_group = st.sidebar.selectbox(
        "Aggregation Level",
        ["Daily", "Weekly", "Monthly", "Yearly"]
    )

    # Apply filters
    filtered_df = df[
        (df["Region"].isin(selected_regions)) &
        (df["Company"].isin(selected_companies))
    ]

    if len(date_range) == 2:

        start_date, end_date = date_range

        filtered_df = filtered_df[
            (filtered_df["Date"] >= pd.to_datetime(start_date)) &
            (filtered_df["Date"] <= pd.to_datetime(end_date))
        ]

    if filtered_df.empty:
        st.warning("No data available for selected filters.")
        return

    # --- KPI METRICS ---
    st.subheader("Key Statistics")

    col1, col2, col3, col4 = st.columns(4)

    total_demand = filtered_df["Demand_MW"].sum()
    peak_demand = filtered_df["Demand_MW"].max()
    avg_daily = filtered_df.groupby("Date")["Demand_MW"].sum().mean()

    peak_row = filtered_df.loc[filtered_df["Demand_MW"].idxmax()]
    peak_date = peak_row["Date"].strftime("%Y-%m-%d")

    with col1:
        st.metric("Total Demand", f"{total_demand:,.0f} MW")

    with col2:
        st.metric("Avg Daily Demand", f"{avg_daily:,.0f} MW")

    with col3:
        st.metric("Peak Demand", f"{peak_demand:,.0f} MW")

    with col4:
        st.metric("Peak Demand Date", peak_date)

    st.divider()

    # --- VISUALIZATIONS ---
    st.divider()
    
    # Row 1: Overall Trend and Regional Distribution
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Overall Demand Trend")
        fig1 = plot_trend(filtered_df, "Aggregate Demand Over Time")
        st.pyplot(fig1)

    with col_chart2:
        st.subheader("Demand by Region")
        plt.style.use('dark_background')
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        region_demand = filtered_df.groupby('Region')['Demand_MW'].sum().sort_values()
        
        bars = ax2.barh(region_demand.index, region_demand.values, color='#FF4081')
        offset = region_demand.max() * 0.02
        for bar in bars:
            width = bar.get_width()
            ax2.text(width + offset, bar.get_y() + bar.get_height()/2, f'{width:,.0f}', 
                     ha='left', va='center', color='white')
        
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        st.pyplot(fig2)

    # Row 2: Company Breakdown (NEW SECTION)
    st.divider()
    st.subheader("Company Performance Breakdown")
    
    col_chart3, col_chart4 = st.columns([2, 1]) # Make the trend chart wider

    with col_chart3:
        # Time-series breakdown by company
        st.write("Daily Demand Contribution per Company")
        fig3, ax3 = plt.subplots(figsize=(12, 5))
        plt.style.use('dark_background')
        
        # Pivot data for stacking: Rows=Date, Columns=Company, Values=Demand
        pivot_df = filtered_df.pivot_table(index='Date', columns='Company', values='Demand_MW', aggfunc='sum')
        
        pivot_df.plot(kind='area', ax=ax3, alpha=0.7, colormap='viridis')
        
        ax3.set_ylabel("MW")
        ax3.legend(loc='upper left', bbox_to_anchor=(1, 1)) # Move legend outside
        ax3.spines['top'].set_visible(False)
        ax3.spines['right'].set_visible(False)
        st.pyplot(fig3)

    with col_chart4:
        # Market Share Pie Chart
        st.write("Current Market Share (Total Demand)")
        fig4, ax4 = plt.subplots()
        company_shares = filtered_df.groupby('Company')['Demand_MW'].sum()
        
        # Using a donut chart for a more modern look
        ax4.pie(company_shares, labels=company_shares.index, autopct='%1.1f%%', 
                startangle=140, colors=plt.cm.viridis(np.linspace(0, 1, len(company_shares))),
                pctdistance=0.85)
        
        # Draw a circle in the middle to make it a donut
        centre_circle = plt.Circle((0,0), 0.70, fc='#0E1117') # Match Streamlit dark theme bg
        fig4.gca().add_artist(centre_circle)
        
        ax4.axis('equal') 
        st.pyplot(fig4)
        
        # Add data labels to bars
        for bar in bars:
            width = bar.get_width()
            # Calculate a tiny offset (e.g., 2% of the max width) so the text doesn't overlap the bar
            offset = region_demand.max() * 0.02 
            
            # Removed 'padding=3' and added the offset to the X coordinate (width)
            ax2.text(width + offset, bar.get_y() + bar.get_height()/2, f'{width:,.0f}', 
                     ha='left', va='center')
            
if __name__ == "__main__":
    main()
