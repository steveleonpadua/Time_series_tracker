import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests
from datetime import datetime, timedelta

# --- 1. PAGE CONFIGURATION ---
# Set wide layout so it looks like a real dashboard
st.set_page_config(page_title="Energy Demand Dashboard", page_icon="⚡", layout="wide")

# --- 2. DATA FETCHING & CACHING ---
# We use @st.cache_data so we don't hit the API every time the user clicks a filter
@st.cache_data(ttl=3600) # Cache clears every hour
def fetch_energy_data():
    """
    Simulates fetching data from your API.
    Replace this with your actual requests.get(API_URL).json() logic.
    """
    # NOTE: Replace the below with your API call:
    # response = requests.get("https://api.your-energy-provider.com/data")
    # df = pd.DataFrame(response.json())
    
    # --- MOCK DATA GENERATION FOR DEMONSTRATION ---
    dates = pd.date_range(end=datetime.today(), periods=90)
    regions = ['North', 'South', 'East', 'West']
    companies = ['EcoPower', 'GridMax', 'Solaris', 'NexGen']
    
    data = []
    for d in dates:
        for r in regions:
            for c in companies:
                base_demand = np.random.randint(100, 500)
                data.append({
                    'Date': d,
                    'Region': r,
                    'Company': c,
                    'Demand_MW': base_demand + np.random.normal(0, 20)
                })
    
    df = pd.DataFrame(data)
    return df

# --- 3. HELPER FUNCTIONS FOR MATPLOTLIB ---
def plot_trend(df, title):
    """Generates a clean, modern Matplotlib figure."""
    # Using a dark background style to mimic popular COVID dashboards
    plt.style.use('dark_background')
    
    fig, ax = plt.subplots(figsize=(10, 4))
    
    # Aggregate data by date
    daily_demand = df.groupby('Date')['Demand_MW'].sum().reset_index()
    
    ax.plot(daily_demand['Date'], daily_demand['Demand_MW'], color='#00E5FF', linewidth=2)
    ax.fill_between(daily_demand['Date'], daily_demand['Demand_MW'], color='#00E5FF', alpha=0.1)
    
    ax.set_title(title, fontsize=14, pad=10, loc='left')
    ax.set_ylabel('Demand (MW)', fontsize=10)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    
    # Clean up borders
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    return fig

# --- 4. MAIN APPLICATION ---
def main():
    st.title("⚡ Energy Demand Tracker")
    st.markdown("Monitor region-wise and company-specific energy consumption.")

    # Load Data
    with st.spinner("Loading API data..."):
        df = fetch_energy_data()

    # --- SIDEBAR FILTERS ---
    st.sidebar.header("Filter Data")
    
    # Get unique values for filters
    all_regions = df['Region'].unique()
    all_companies = df['Company'].unique()

    selected_regions = st.sidebar.multiselect("Select Region(s)", all_regions, default=all_regions)
    selected_companies = st.sidebar.multiselect("Select Company(s)", all_companies, default=all_companies)

    # Apply Filters
    filtered_df = df[
        (df['Region'].isin(selected_regions)) & 
        (df['Company'].isin(selected_companies))
    ]

    if filtered_df.empty:
        st.warning("No data available for the selected filters.")
        return

    # --- KPI METRICS ---
    st.subheader("Key Statistics")
    col1, col2, col3, col4 = st.columns(4)

    # Calculations
    total_demand = filtered_df['Demand_MW'].sum()
    peak_demand = filtered_df['Demand_MW'].max()
    avg_daily = filtered_df.groupby('Date')['Demand_MW'].sum().mean()
    
    # Find the date of peak demand
    peak_date_row = filtered_df.loc[filtered_df['Demand_MW'].idxmax()]
    peak_date = peak_date_row['Date'].strftime('%Y-%m-%d')

    # Display Metrics (Streamlit handles the formatting beautifully)
    with col1:
        st.metric("Total Demand (MW)", f"{total_demand:,.0f}")
    with col2:
        st.metric("Avg Daily Demand (MW)", f"{avg_daily:,.0f}")
    with col3:
        st.metric("Peak Demand (MW)", f"{peak_demand:,.0f}")
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