# Time_series_tracker

`ingest.py` fetches the most recent electricity demand data from the U.S. Energy Information Administration API and stores a versioned raw snapshot of the response. It processes confirmed demand records to update timezone- and respondent-level time series, overwriting values if revisions are detected in the latest ingestion window.