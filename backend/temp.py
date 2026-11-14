import requests
from collections import defaultdict
from statistics import mean
import calendar
import csv

# =====================================
# CONFIGURATION
# =====================================
LAT = 32.2211
LON = 35.2544

HISTORY_START = 2001
HISTORY_END = 2025
PREDICTION_YEAR = 2027

URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

params = {
    "parameters": "T2M,T2M_MAX,T2M_MIN",
    "community": "AG",
    "latitude": LAT,
    "longitude": LON,
    "start": f"{HISTORY_START}0101",
    "end": f"{HISTORY_END}1231",
    "format": "JSON",
    "units": "METRIC"
}

# =====================================
# GET NASA DATA
# =====================================
response = requests.get(URL, params=params, timeout=120)
response.raise_for_status()

data = response.json()["properties"]["parameter"]

monthly = defaultdict(
    lambda: {"avg": [], "max": [], "min": []}
)

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

# =====================================
# ESTIMATE MONTHLY TEMPERATURES
# =====================================
results = []

print(f"\nEstimated Monthly Temperatures - {PREDICTION_YEAR}\n")

for month in range(1, 13):
    samples = monthly[month]

    if not all(samples[k] for k in ("avg", "max", "min")):
        print(f"{PREDICTION_YEAR}-{month:02d}: No data")
        continue

    avg = round(mean(samples["avg"]), 2)
    max_temp = round(mean(samples["max"]), 2)
    min_temp = round(mean(samples["min"]), 2)

    result = {
        "month": f"{PREDICTION_YEAR}-{month:02d}",
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

# =====================================
# SAVE CSV
# =====================================
with open("temperature_monthly_2027.csv", "w", newline="") as file:
    writer = csv.DictWriter(
        file,
        fieldnames=["month", "average", "maximum", "minimum"]
    )
    writer.writeheader()
    writer.writerows(results)

print("\nSaved: temperature_monthly_2027.csv")