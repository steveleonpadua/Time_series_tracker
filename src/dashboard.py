import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

st.set_page_config(page_title="Energy Demand Dashboard", page_icon="⚡", layout="wide")


# -------------------------------
# LOAD DATA
# -------------------------------
@st.cache_data
def load_processed_data():

    tz_dir = "../data_processed/timezone"
    resp_dir = "../data_processed/respondent"

    tz_frames = []
    resp_frames = []

    for f in os.listdir(tz_dir):

        df = pd.read_csv(os.path.join(tz_dir, f))
        df["Region"] = f.replace(".csv","")
        df["Date"] = pd.to_datetime(df["period"])
        df["Demand_MW"] = df["value"]

        tz_frames.append(df)

    for f in os.listdir(resp_dir):

        df = pd.read_csv(os.path.join(resp_dir, f))
        df["Company"] = f.replace(".csv","")
        df["Date"] = pd.to_datetime(df["period"])
        df["Demand_MW"] = df["value"]

        resp_frames.append(df)

    tz_df = pd.concat(tz_frames)
    resp_df = pd.concat(resp_frames)

    return tz_df, resp_df


# -------------------------------
# TIME AGGREGATION
# -------------------------------
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


# -------------------------------
# TREND PLOT
# -------------------------------
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


# -------------------------------
# MAIN APP
# -------------------------------
def main():

    st.title("⚡ Energy Demand Tracker")
    st.markdown("Monitoring electricity demand using the EIA dataset.")

    with st.spinner("Loading dataset..."):
        tz_df, resp_df = load_processed_data()

    st.sidebar.header("Filters")

    # ---- DATE RANGE FILTER ----
    min_date = resp_df["Date"].min()
    max_date = resp_df["Date"].max()

    date_range = st.sidebar.date_input(
        "Date Range",
        [min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )

    if len(date_range) == 2:

        start_date, end_date = date_range

        tz_df = tz_df[
            (tz_df["Date"] >= pd.to_datetime(start_date)) &
            (tz_df["Date"] <= pd.to_datetime(end_date))
        ]

        resp_df = resp_df[
            (resp_df["Date"] >= pd.to_datetime(start_date)) &
            (resp_df["Date"] <= pd.to_datetime(end_date))
        ]


    # ---- REGION FILTER ----
    regions = tz_df["Region"].unique()

    selected_regions = st.sidebar.multiselect(
        "Timezone",
        regions,
        default=regions
    )

    tz_df = tz_df[tz_df["Region"].isin(selected_regions)]


    # ---- RESPONDENT FILTER ----
    companies = resp_df["Company"].unique()

    selected_companies = st.sidebar.multiselect(
        "Respondent",
        companies,
        default=companies
    )

    resp_df = resp_df[resp_df["Company"].isin(selected_companies)]


    # ---- AGGREGATION LEVEL ----
    time_group = st.sidebar.selectbox(
        "Aggregation Level",
        ["Daily","Weekly","Monthly","Yearly"]
    )


    # --------------------------
    # KPI METRICS
    # --------------------------

    st.subheader("Key Statistics")

    col1, col2, col3, col4 = st.columns(4)

    total_demand = resp_df["Demand_MW"].sum()
    peak_demand = resp_df["Demand_MW"].max()
    avg_daily = resp_df.groupby("Date")["Demand_MW"].sum().mean()

    peak_row = resp_df.loc[resp_df["Demand_MW"].idxmax()]

    peak_date = peak_row["Date"]
    if isinstance(peak_date, pd.Series):
        peak_date = peak_date.iloc[0]

    peak_date = pd.to_datetime(peak_date).strftime("%Y-%m-%d")

    col1.metric("Total Demand", f"{total_demand:,.0f} MW")
    col2.metric("Avg Daily Demand", f"{avg_daily:,.0f} MW")
    col3.metric("Peak Demand", f"{peak_demand:,.0f} MW")
    col4.metric("Peak Demand Date", peak_date)


    # --------------------------
    # CHARTS ROW
    # --------------------------

    st.divider()

    col_chart1, col_chart2 = st.columns(2)

    # ---- DEMAND TREND ----
    with col_chart1:

        st.subheader("Demand Trend")

        fig1 = plot_trend(
            resp_df,
            "Aggregate Demand Over Time",
            time_group
        )

        st.pyplot(fig1)


    # ---- DEMAND BY REGION ----
    with col_chart2:

        st.subheader("Demand by Region")

        plt.style.use("dark_background")

        fig2, ax2 = plt.subplots(figsize=(10,4))

        region_demand = tz_df.groupby("Region")["Demand_MW"].sum().sort_values()

        bars = ax2.barh(region_demand.index, region_demand.values, color="#FF4081")

        offset = region_demand.max() * 0.02

        for bar in bars:

            width = bar.get_width()

            ax2.text(
                width + offset,
                bar.get_y() + bar.get_height()/2,
                f"{width:,.0f}",
                ha="left",
                va="center",
                color="white"
            )

        ax2.spines["top"].set_visible(False)
        ax2.spines["right"].set_visible(False)

        st.pyplot(fig2)


    # --------------------------
    # COMPANY ANALYSIS
    # --------------------------

    st.divider()

    st.subheader("Company Performance")

    col_chart3, col_chart4 = st.columns([2,1])


    # ---- COMPANY TREND ----
    with col_chart3:

        st.write("Demand Contribution by Major Respondents")

        fig3, ax3 = plt.subplots(figsize=(12,5))

        pivot_df = resp_df.pivot_table(
            index="Date",
            columns="Company",
            values="Demand_MW",
            aggfunc="sum"
        )

        totals = pivot_df.sum().sort_values(ascending=False)

        top_n = 8
        top_companies = totals.head(top_n).index

        top_df = pivot_df[top_companies]

        others = pivot_df.drop(columns=top_companies).sum(axis=1)

        top_df["Others"] = others

        top_df.plot.area(
            ax=ax3,
            alpha=0.8,
            colormap="viridis"
        )

        ax3.set_ylabel("Demand (MW)")
        ax3.legend(loc="upper left")

        ax3.spines["top"].set_visible(False)
        ax3.spines["right"].set_visible(False)

        st.pyplot(fig3)


    # ---- MARKET SHARE ----
    with col_chart4:

        st.write("Market Share (Top Operators)")

        fig4, ax4 = plt.subplots()

        company_shares = resp_df.groupby("Company")["Demand_MW"].sum()

        company_shares = company_shares.sort_values(ascending=False)

        top_n = 8
        top_companies = company_shares[:top_n]

        others = company_shares[top_n:].sum()

        if others > 0:
            top_companies["Others"] = others

        colors = plt.cm.viridis(np.linspace(0,1,len(top_companies)))

        ax4.pie(
            top_companies,
            labels=top_companies.index,
            autopct="%1.1f%%",
            startangle=140,
            colors=colors,
            pctdistance=0.8
        )

        centre_circle = plt.Circle((0,0),0.65,fc="#0E1117")

        fig4.gca().add_artist(centre_circle)

        ax4.axis("equal")

        st.pyplot(fig4)


if __name__ == "__main__":
    main()
