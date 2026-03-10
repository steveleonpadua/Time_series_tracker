'''
To ingest daily eletricity demand data from US EIA API
'''

import requests
import pandas as pd
from datetime import datetime
import os

from datetime import datetime, timedelta

API_KEY = "qEGHg1McUW8piAWNvmQRgAhmrRpuXq48DfauTyj3"

URL = "https://api.eia.gov/v2/electricity/rto/daily-region-data/data/"


def fetch_recent_data():

    end = datetime.today()
    start = end - timedelta(days=2)

    params = {
        "api_key": API_KEY,
        "frequency": "daily",
        "data[0]": "value",
        "start": start.strftime("%Y-%m-%d"),
        "end": end.strftime("%Y-%m-%d"),
        "length": 5000
    }

    r = requests.get(URL, params=params)

    data = r.json()["response"]["data"]

    df = pd.DataFrame(data)

    df["period"] = pd.to_datetime(df["period"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.dropna(subset=["value"])

    print("\nFetched periods:")
    print(sorted(df["period"].unique()))

    return df


def save_raw(df):

    os.makedirs("../data_raw", exist_ok=True)
    today = datetime.today().strftime("%Y-%m-%d")
    path = f"../data_raw/raw_{today}.csv"
    df.to_csv(path, index=False)
    return path


def load_previous_raw():

    if not os.path.exists("../data_raw"):
        return None
    files = sorted(os.listdir("../data_raw"))
    if len(files) < 2:
        return None
    prev = files[-2]
    return pd.read_csv(f"../data_raw/{prev}")


def detect_corrections(old_df, new_df):

    old_df["period"] = pd.to_datetime(old_df["period"])
    merged = old_df.merge(
        new_df,
        on=["period", "respondent", "timezone", "type"],
        suffixes=("_old", "_new")
    )
    corrections = merged[
        merged["value_old"] != merged["value_new"]
    ]
    return corrections


def save_revision_log(df):

    if len(df) == 0:
        return
    os.makedirs("revisions", exist_ok=True)
    today = datetime.today().strftime("%Y-%m-%d")
    df.to_csv(f"revisions/revision_{today}.csv", index=False)


def filter_demand(df):

    df = df[df["type"] == "D"]
    valid_periods = df["period"].unique()
    print("Valid demand periods:", sorted(valid_periods))
    df = df[df["period"].isin(valid_periods)]
    return df


def aggregate_timezone(df):

    grouped = (
        df.groupby(["period", "timezone"])["value"]
        .sum()
        .reset_index()
    )
    print("\nGrouped periods:")
    print(sorted(grouped["period"].unique()))
    return grouped


def aggregate_respondent(df):

    grouped = (
        df.groupby(["period", "respondent"])["value"]
        .sum()
        .reset_index()
    )
    print("Respondent periods:", sorted(grouped["period"].unique()))
    return grouped


def update_timezone_file(tz_df, path):

    tz_df = tz_df.sort_values("period")
    if os.path.exists(path):
        old = pd.read_csv(path)
        old["period"] = pd.to_datetime(old["period"])
        combined = pd.concat([old, tz_df])
        combined = combined.sort_values("period")
        combined = combined.drop_duplicates(
            subset=["period"],
            keep="last"
        )
    else:
        combined = tz_df
    combined.to_csv(path, index=False)


def save_by_timezone(df):

    os.makedirs("../data_processed/timezone", exist_ok=True)
    for tz in df["timezone"].unique():
        tz_df = df[df["timezone"] == tz][["period", "value"]]
        path = f"../data_processed/timezone/{tz}.csv"
        update_timezone_file(tz_df, path)


def save_by_respondent(df):

    os.makedirs("../data_processed/respondent", exist_ok=True)
    for r in df["respondent"].unique():
        r_df = df[df["respondent"] == r][["period", "value"]]
        path = f"../data_processed/respondent/{r}.csv"
        update_timezone_file(r_df, path)


def run_pipeline():

    print("Pipeline started")
    df = fetch_recent_data()
    save_raw(df)
    df = filter_demand(df)
    tz_grouped = aggregate_timezone(df)
    save_by_timezone(tz_grouped)
    respondent_grouped = aggregate_respondent(df)
    save_by_respondent(respondent_grouped)
    print("Pipeline finished successfully")


if __name__ == "__main__":
    run_pipeline()