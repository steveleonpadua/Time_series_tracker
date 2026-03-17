
# Time Series Tracker — Electricity Demand Monitoring

> DS3294 Data Science Practice — Mini Project — Team 15

**Team Members:**  
Steve Leon Padua · Aatif Mashkoor · Mukul · Akshat Agarwal

---

# Project Overview

This project implements a **time‑series monitoring pipeline for U.S. electricity demand data** using the EIA API.

The system automatically downloads electricity demand data, stores versioned raw snapshots, detects revisions in historical values, and builds daily time‑series datasets grouped by geographic region and grid operator. The processed data is visualised through an interactive Streamlit dashboard.

The project demonstrates a complete monitoring workflow:

- **Data ingestion** from a real‑world API  
- **Versioned raw data storage**  
- **Detection of revisions in historical records**  
- **Aggregation of time series by region and operator**  
- **Interactive dashboard visualisation**  

---

# Data Source

The data is obtained from the **U.S. Energy Information Administration (EIA)** Open Data API.

| Property | Value |
|---|---|
| Dataset | EIA Electricity Demand |
| API endpoint | https://api.eia.gov/v2/electricity/rto/daily-region-data/data/ |
| Metric | Electricity demand (MW) |
| Frequency | Daily |
| Coverage | U.S. grid operators and time zones |
| Access | Free with API key |

The API provides demand data for **balancing authorities and regional transmission operators**, including:

- PJM — Eastern U.S.
- ERCOT — Texas
- CAISO — California
- MISO — Midwest
- NYISO — New York
- SPP — Great Plains

Each observation contains:

period — date of demand  
respondent — grid operator  
timezone — reporting timezone  
value — electricity demand  
type — data type (D = confirmed demand)

Only **confirmed demand (`type = D`)** is used in the pipeline.

---

# Repository Structure

```
Time_series_tracker/

src/
│
├── ingest.py              # Daily data ingestion pipeline
├── bootstrap_history.py   # Download historical data
├── dashboard.py           # Streamlit dashboard
│
data_raw/                  # Raw API snapshots
│   raw_<date>.csv
│
data_processed/
│   ├── timezone/
│   │    Central.csv
│   │    Eastern.csv
│   │    Pacific.csv
│   │
│   └── respondent/
│        PJM.csv
│        ERCOT.csv
│        CAISO.csv
│
revisions/                 # Detected data corrections
│   revision_<date>.csv
│
README.md
requirements.txt
```

---

# Pipeline Overview

```
EIA API
   │
   ▼
ingest.py
   │
   ├── Save raw snapshot
   │     data_raw/raw_<date>.csv
   │
   ├── Detect revisions
   │     revisions/revision_<date>.csv
   │
   ├── Filter confirmed demand
   │
   ├── Aggregate by timezone
   │     data_processed/timezone/
   │
   └── Aggregate by respondent
         data_processed/respondent/
```

The pipeline runs daily and updates the time‑series datasets automatically.

---

# Data Versioning and Revisions

Energy datasets are often **revised after initial publication**.

To handle this, the pipeline stores a **raw snapshot of every API response**:

```
data_raw/raw_2026-03-10.csv
data_raw/raw_2026-03-11.csv
```

Each new snapshot is compared with the previous snapshot to detect corrections in historical data.

If a value changes, the difference is recorded in:

```
revisions/revision_<date>.csv
```

This provides an audit trail of all data revisions.

---

# Historical Data Bootstrap

To initialise the dataset with multiple years of data, the script:

```
bootstrap_history.py
```

downloads historical records using the API and populates the processed datasets before the daily pipeline begins.

---

# Dashboard

The dashboard is built using **Streamlit**.

It visualises the processed electricity demand data and provides interactive filters.

## Features

- Select **date range**
- Aggregate by **day / week / month / year**
- Filter by **timezone**
- Filter by **grid operator (respondent)**

## Visualisations

- Demand trend over time
- Demand distribution by region
- Summary statistics

The dashboard reads directly from:

```
data_processed/
```

so it always displays the latest pipeline results.

---


# Author Contributions

| Team Member | Responsibilities |
|----|----|
| Akshat Agarwal | Data ingestion pipeline, API integration, revision detection |
| Steve Leon Padua | Data analysis and validation |
| Aatif Mashkoor | Streamlit dashboard |
| Mukul | Streamlit dashboard |

---

# License

MIT License
