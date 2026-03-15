# Time_series_tracker

# Progress
`ingest.py` fetches the most recent electricity demand data from the U.S. Energy Information Administration API and stores a versioned raw snapshot of the response. It processes confirmed demand records to update timezone- and respondent-level time series, overwriting values if revisions are detected in the latest ingestion window.

# Plan:
- Find data source
- Ingest data
- Save after versioning and groupping by timezone and company

- Deal with missing values by interpolation, keeping track of dates
- Find outliers (4 * std)
- Group by different time periods
- Calculate statistics for the data

- Interactive dashboard which lets you choose which data to be plotted, for what time period
- Still a work in progress
