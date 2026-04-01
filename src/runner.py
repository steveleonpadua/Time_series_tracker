import time
import subprocess
import os
import pandas as pd
from datetime import datetime, timedelta

DATA_PATH = "../data_processed/respondent"


def get_latest_date():

    if not os.path.exists(DATA_PATH):
        return None

    files = os.listdir(DATA_PATH)

    if not files:
        return None

    df = pd.read_csv(os.path.join(DATA_PATH, files[0]))

    df["period"] = pd.to_datetime(df["period"])

    return df["period"].max()


def check_missing_days():

    last_date = get_latest_date()

    if last_date is None:
        return True

    today = datetime.today()

    delta = (today - last_date).days

    print("Last data date:", last_date.date())
    print("Days missing:", delta)

    return delta > 2   # threshold


def run_script(script):

    print(f"Running {script}...")

    result = subprocess.run(
        ["python", script],
        capture_output=True,
        text=True
    )

    print(result.stdout)

    if result.returncode != 0:
        print("Error:", result.stderr)


def main():

    print("Starting continuous runner...")

    while True:

        now = datetime.now()

        # run once per day (e.g. 9 AM)
        if now.hour == 9:

            print("\n--- DAILY JOB START ---")

            if check_missing_days():

                print("Missing data detected → running bootstrap")

                run_script("bootstrap_history.py")

            else:

                print("Running daily ingest")

                run_script("ingest.py")

            print("--- JOB COMPLETE ---\n")

            # sleep 1 hour to avoid duplicate runs
            time.sleep(3600)

        # check every 10 minutes
        time.sleep(600)


if __name__ == "__main__":
    main()
