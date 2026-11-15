import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]

# The data scripts live at the backend root, next to the app package. uvicorn is
# normally started with --app-dir backend, but add it explicitly so the imports
# below work regardless of the working directory the server was launched from.
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import moisture
import nitrogen
import pH
import rain
import temp


def rain_rows(lat, lon, months):
    result = rain.get_annual_precipitation(lat, lon, "next", 1)
    return result["monthly"][:months]


def temperature_rows(lat, lon, months):
    return temp.monthly_estimates(lat, lon, months)


def ph_rows(lat, lon, _months):
    return pH.to_rows(pH.get_soil_ph(lat, lon))


def nitrogen_rows(lat, lon, _months):
    result = nitrogen.get_nitrogen(lat, lon)
    return [result]


def moisture_rows(lat, lon, _months):
    return [moisture.get_soil_moisture(lat, lon)]


DATASETS = {
    "rain": rain_rows,
    "temperature": temperature_rows,
    "ph": ph_rows,
    "nitrogen": nitrogen_rows,
    "moisture": moisture_rows,
}

# pH comes from the USDA SSURGO survey, which only covers the United States.
COVERAGE_NOTES = {
    "ph": "No soil survey data for this point. Soil pH comes from the USDA survey, which covers the United States only.",
}


def run_dataset(name, lat, lon, months):
    try:
        rows = DATASETS[name](lat, lon, months)
    except Exception as error:
        return {"rows": [], "error": f"{type(error).__name__}: {error}"}

    if not rows:
        return {"rows": [], "error": COVERAGE_NOTES.get(name, "No data available for this location.")}
    return {"rows": rows, "error": None}


def analyze(lat, lon, months=12):
    """Fetch every dataset for one location; a failing source never fails the rest."""
    with ThreadPoolExecutor(max_workers=len(DATASETS)) as pool:
        futures = {
            name: pool.submit(run_dataset, name, lat, lon, months) for name in DATASETS
        }
        results = {name: future.result() for name, future in futures.items()}

    return {"lat": lat, "lon": lon, "months": months, **results}
