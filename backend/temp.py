import argparse
import csv
from collections import defaultdict
from datetime import date
from statistics import mean

import requests

import requests

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

HISTORY_START = 2001
HISTORY_END = 2025


# =====================================
# CROP SEASONS
# months = how many months the crop needs
# start  = default planting month (1-12)
# =====================================
CROPS = {
    "wheat":      {"months": 5, "start": 11},
    "barley":     {"months": 5, "start": 11},
    "lentil":     {"months": 5, "start": 11},
    "chickpea":   {"months": 5, "start": 2},
    "onion":      {"months": 5, "start": 10},
    "potato":     {"months": 4, "start": 2},
    "tomato":     {"months": 4, "start": 3},
    "corn":       {"months": 4, "start": 4},
    "watermelon": {"months": 4, "start": 3},
    "pepper":     {"months": 5, "start": 3},
    "eggplant":   {"months": 5, "start": 3},
    "cucumber":   {"months": 3, "start": 3},
    "squash":     {"months": 3, "start": 3},
}


def season_months(year, start_month, n_months):
    """[(year, month), ...] for the season. Wraps into next year if needed."""
    if not 1 <= start_month <= 12:
        raise ValueError("Start month must be between 1 and 12")
    return [
        (year + (start_month - 1 + i) // 12, (start_month - 1 + i) % 12 + 1)
        for i in range(n_months)
    ]


def get_monthly_average_temp(lat, lon):
    """Return {month: average temperature in C} from NASA history."""
    params = {
        "parameters": "T2M",
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
    data = response.json()["properties"]["parameter"]["T2M"]

    monthly = defaultdict(list)
    for day, value in data.items():
        if value is not None and value > -900:
            monthly[int(day[4:6])].append(value)

    return {month: round(mean(values), 2) for month, values in monthly.items()}


def main():
    parser = argparse.ArgumentParser(description="Average temperature for a crop season")
    parser.add_argument("--crop", default="wheat", help=", ".join(sorted(CROPS)))
    parser.add_argument("--start", type=int, help="planting month 1-12 (default: crop's usual month)")
    parser.add_argument("--lat", type=float, default=LAT)
    parser.add_argument("--lon", type=float, default=LON)
    parser.add_argument("--year", type=int, default=PREDICTION_YEAR)
    args = parser.parse_args()

    crop = args.crop.strip().lower()
    if crop not in CROPS:
        parser.error(f"Unknown crop '{args.crop}'. Available: {', '.join(sorted(CROPS))}")

    info = CROPS[crop]
    start = args.start or info["start"]

    try:
        months = season_months(args.year, start, info["months"])
        averages = get_monthly_average_temp(args.lat, args.lon)
    except (ValueError, requests.RequestException, KeyError) as error:
        parser.exit(1, f"Error: {error}\n")

    print(f"\n{crop.title()} - {info['months']} months starting {args.year}-{start:02d}\n")

    results = []
    for year, month in months:
        if month not in averages:
            print(f"{year}-{month:02d}: No data")
            continue
        results.append({"month": f"{year}-{month:02d}", "average": averages[month]})
        print(f"{year}-{month:02d} | Average: {averages[month]} °C")

    if not results:
        parser.exit(1, "No temperature data found.\n")

    season_avg = round(mean(r["average"] for r in results), 2)
    print(f"\nSeason average: {season_avg} °C")

    filename = f"temperature_{crop}_{args.year}.csv"
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["month", "average"])
        writer.writeheader()
        writer.writerows(results)
        writer.writerow({"month": "season_average", "average": season_avg})

    print(f"Saved: {filename}")


if __name__ == "__main__":
    main()
