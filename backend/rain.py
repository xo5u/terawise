"""Historical annual rainfall and a historical-average next-year estimate."""

import argparse
import calendar
import csv
import json
import math
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone

import requests

API = "https://archive-api.open-meteo.com/v1/archive"
ARCHIVE_DELAY_DAYS = 5


def shift_year(day, years):
    year = day.year + years
    return day.replace(year=year, day=min(day.day, calendar.monthrange(year, day.month)[1]))


def validate_location(lat, lon):
    if not math.isfinite(lat) or not -90 <= lat <= 90:
        raise ValueError("Latitude must be between -90 and 90")
    if not math.isfinite(lon) or not -180 <= lon <= 180:
        raise ValueError("Longitude must be between -180 and 180")


def query_rainfall(lat, lon, start_date, end_date):
    validate_location(lat, lon)
    response = requests.get(
        API,
        params={
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily": "rain_sum",
            "precipitation_unit": "mm",
            "timezone": "GMT",
        },
        timeout=60,
    )
    response.raise_for_status()
    daily = response.json().get("daily", {})
    readings = {}
    for timestamp, value in zip(daily.get("time", []), daily.get("rain_sum", [])):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if not math.isfinite(value) or value < 0:
            continue
        day = date.fromisoformat(timestamp)
        if start_date <= day <= end_date:
            readings[day] = value
    return readings


def require_complete(readings, start_date, end_date):
    expected = (end_date - start_date).days + 1
    if len(readings) != expected:
        raise RuntimeError(
            f"Incomplete rainfall data: {len(readings)} of {expected} days available "
            f"for {start_date} through {end_date}. Cannot report a full-year total."
        )


def get_precipitation(lat, lon):
    """Return the latest available daily rainfall."""
    end = datetime.now(timezone.utc).date() - timedelta(days=ARCHIVE_DELAY_DAYS)
    readings = query_rainfall(lat, lon, end - timedelta(days=2), end)
    if not readings:
        raise RuntimeError("No valid rainfall data found.")
    latest = max(readings)
    return {"date": latest.isoformat(), "rainfall_mm": readings[latest]}


def get_annual_precipitation(lat, lon, period="past", *, today=None):
    """Return a complete past year or an explicitly labeled next-year estimate."""
    validate_location(lat, lon)
    today = today or datetime.now(timezone.utc).date()
    if period not in ("past", "next"):
        raise ValueError("Period must be 'past' or 'next'")

    if period == "past":
        end = today - timedelta(days=ARCHIVE_DELAY_DAYS)
        start = shift_year(end, -1) + timedelta(days=1)
        readings = query_rainfall(lat, lon, start, end)
        require_complete(readings, start, end)
        daily_values = readings
        metadata = {
            "data_type": "historical_reanalysis",
            "note": f"Latest complete 12 months ending {ARCHIVE_DELAY_DAYS} days ago; rainfall excludes snow.",
        }
    else:
        # Five complete calendar years avoid partial seasonal samples.
        last_year = (today - timedelta(days=ARCHIVE_DELAY_DAYS)).year - 1
        baseline_start = date(last_year - 4, 1, 1)
        baseline_end = date(last_year, 12, 31)
        readings = query_rainfall(lat, lon, baseline_start, baseline_end)
        require_complete(readings, baseline_start, baseline_end)
        monthly_samples = defaultdict(list)
        for day, value in readings.items():
            monthly_samples[day.month].append(value)
        monthly_means = {
            month: sum(values) / len(values) for month, values in monthly_samples.items()
        }
        start = today + timedelta(days=1)
        end = shift_year(today, 1)
        daily_values = {}
        day = start
        while day <= end:
            daily_values[day] = monthly_means[day.month]
            day += timedelta(days=1)
        metadata = {
            "data_type": "historical_average_estimate",
            "baseline_start_date": baseline_start.isoformat(),
            "baseline_end_date": baseline_end.isoformat(),
            "note": "Estimate from five years of monthly average daily rainfall, not a weather forecast. Actual rainfall may differ. Rainfall excludes snow.",
        }

    monthly_totals = defaultdict(float)
    monthly_days = defaultdict(int)
    for day, value in sorted(daily_values.items()):
        month = day.strftime("%Y-%m")
        monthly_totals[month] += value
        monthly_days[month] += 1

    return {
        "period": period,
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "days_counted": len(daily_values),
        "total_rainfall_mm": round(sum(daily_values.values()), 2),
        "monthly": [
            {"month": month, "days_counted": monthly_days[month], "rainfall_mm": round(total, 2)}
            for month, total in monthly_totals.items()
        ],
        **metadata,
    }


def save_csv(result, filename="rain_monthly.csv"):
    """Save the monthly rainfall to a CSV file."""
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["month", "days_counted", "rainfall_mm"])
        writer.writeheader()
        writer.writerows(result["monthly"])
        writer.writerow({
            "month": "total",
            "days_counted": result["days_counted"],
            "rainfall_mm": result["total_rainfall_mm"],
        })
    return filename


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lat", type=float, default=32.2211)
    parser.add_argument("--lon", type=float, default=35.2544)
    parser.add_argument("--period", choices=("past", "next"), default="next")
    parser.add_argument("--year", action="store_true", help="Compatibility flag; annual output is now the default.")
    args = parser.parse_args()
    try:
        validate_location(args.lat, args.lon)
    except ValueError as exc:
        parser.error(str(exc))
    try:
        result = get_annual_precipitation(args.lat, args.lon, args.period)
    except (requests.RequestException, RuntimeError, ValueError) as exc:
        parser.exit(1, f"Rainfall request failed: {exc}\n")
    print(json.dumps(result, indent=2))
    print(f"\nSaved: {save_csv(result)}")


if __name__ == "__main__":
    main()