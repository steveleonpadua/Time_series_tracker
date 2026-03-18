import requests
import pandas as pd
from datetime import datetime, timedelta
import time

from ingest import (
    filter_demand,
    aggregate_timezone,
    aggregate_respondent,
    save_by_timezone,
    save_by_respondent
)

API_KEY = "qEGHg1McUW8piAWNvmQRgAhmrRpuXq48DfauTyj3"

URL = "https://api.eia.gov/v2/electricity/rto/daily-region-data/data/"

START = datetime(2024, 1, 1)
END = datetime(2024, 12, 31)


def fetch_day(date):

    date_str = date.strftime("%Y-%m-%d")

    params = {
        "api_key": API_KEY,
        "frequency": "daily",
        "data[0]": "value",
        "start": date_str,
        "end": date_str,
        "length": 5000
    }

    r = requests.get(URL, params=params, timeout=60)

    data = r.json()["response"]["data"]

    df = pd.DataFrame(data)

    if df.empty:
        return df

    df["period"] = pd.to_datetime(df["period"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")

    df = df.dropna(subset=["value"])

    return df


def process_week(frames):

    if not frames:
        return

    df = pd.concat(frames)

    print("Processing week with rows:", len(df))

    df = filter_demand(df)

    tz = aggregate_timezone(df)
    save_by_timezone(tz)

    resp = aggregate_respondent(df)
    save_by_respondent(resp)


def main():

    current = START

    week_frames = []
    day_counter = 0

    while current <= END:

        try:

            print("Downloading:", current.date())

            df = fetch_day(current)

            if not df.empty:
                week_frames.append(df)

        except Exception as e:

            print("Error:", e)

        day_counter += 1

        # every 7 days → process and save
        if day_counter == 7:

            process_week(week_frames)

            week_frames = []
            day_counter = 0

        current += timedelta(days=1)

        time.sleep(0.5)

    # process remaining days
    if week_frames:
        process_week(week_frames)

    print("Bootstrap finished.")


if __name__ == "__main__":
    main()