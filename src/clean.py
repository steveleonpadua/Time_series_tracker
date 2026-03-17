"""
clean.py  -  Data cleaning for the EIA electricity-demand time series.
 
What this script does
---------------------
1. Loads every raw snapshot produced by ingest.py.
2. Harmonises column names and data types.
3. Flags and interpolates missing values, keeping a separate log.
4. Detects outliers with the 4 x standard-deviation rule.
5. Saves a clean Parquet file and a JSON log of every change made.
 
Usage
-----
    python clean.py
 
Output files  (written to data/clean/)
---------------------------------------
    clean_demand.parquet  - cleaned time series
    cleaning_log.json     - log of missing dates, outliers, and actions taken
"""
