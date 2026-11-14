import argparse
import csv
from collections import defaultdict
from datetime import date
from statistics import mean

import requests

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

HISTORY_START = 2001
HISTORY_END = 2025


def fetch_monthly_history(lat, lon):
    params = {
        "parameters": "T2M,T2M_MAX,T2M_MIN",
        "community": "AG",
        "latitude": lat,
        "longitude": lon,
        "start": f"{HISTORY_START}0101",
        "end": f"{HISTORY_END}1231",
        "format": "JSON",
        "units": "METRIC"
    }

    response = requests.get(URL, params=params, timeout=120)
    response.raise_for_status()

    data = response.json()["properties"]["parameter"]

    monthly = defaultdict(lambda: {"avg": [], "max": [], "min": []})

    for day, temp in data["T2M"].items():
        month = int(day[4:6])

        values = {
            "avg": temp,
            "max": data["T2M_MAX"].get(day),
            "min": data["T2M_MIN"].get(day)
        }

        for name, value in values.items():
            if value is not None and value > -900:
                monthly[month][name].append(value)

    return monthly


def next_n_months(start_year, start_month, n):
    year, month = start_year, start_month
    for _ in range(n):
        yield year, month
        month += 1
        if month > 12:
            month = 1
            year += 1


def main():
    parser = argparse.ArgumentParser(description="Estimate monthly temperatures from NASA POWER history.")
    parser.add_argument("--lat", type=float, default=32.2211)
    parser.add_argument("--lon", type=float, default=35.2544)
    parser.add_argument("--months", type=int, default=12, help="How many upcoming months to estimate (n).")
    args = parser.parse_args()

    if args.months < 1:
        parser.error("--months must be an integer >= 1")

    monthly = fetch_monthly_history(args.lat, args.lon)

    today = date.today()
    start_year = today.year if today.month < 12 else today.year + 1
    start_month = today.month + 1 if today.month < 12 else 1

    results = []
    print(f"\nEstimated Monthly Temperatures - next {args.months} month(s)\n")

    for year, month in next_n_months(start_year, start_month, args.months):
        samples = monthly[month]

        if not all(samples[k] for k in ("avg", "max", "min")):
            print(f"{year}-{month:02d}: No data")
            continue

        avg = round(mean(samples["avg"]), 2)
        max_temp = round(mean(samples["max"]), 2)
        min_temp = round(mean(samples["min"]), 2)

        result = {
            "month": f"{year}-{month:02d}",
            "average": avg,
            "maximum": max_temp,
            "minimum": min_temp
        }

        results.append(result)

        print(
            f'{result["month"]} | '
            f'Average: {avg} °C | '
            f'Max: {max_temp} °C | '
            f'Min: {min_temp} °C'
        )

    with open("temperature_monthly_estimate.csv", "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["month", "average", "maximum", "minimum"])
        writer.writeheader()
        writer.writerows(results)

    print("\nSaved: temperature_monthly_estimate.csv")


if __name__ == "__main__":
    main()
