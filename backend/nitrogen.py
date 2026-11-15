import csv
import math

import numpy as np
import requests
from rasterio.io import MemoryFile
from rasterio.transform import xy

LAT = 32.2211
LON = 35.2544

WCS_URL = "https://maps.isric.org/mapserv"
COVERAGE = "nitrogen_0-5cm_mean"
DEPTH = "0-5cm"
# SoilGrids serves nitrogen in cg/kg; dividing by 100 gives g/kg.
UNIT_DIVISOR = 100

# Half-widths (degrees) of the windows fetched around the point, smallest first.
# 0.005 deg is a 4x4 block of native 250 m cells; larger windows only load if
# the point itself is masked (urban, water, bare rock).
SEARCH_HALF_WIDTHS_DEG = [0.005, 0.025, 0.1, 0.4]


def validate_location(lat, lon):
    if not math.isfinite(lat) or not -90 <= lat <= 90:
        raise ValueError("Latitude must be between -90 and 90")
    if not math.isfinite(lon) or not -180 <= lon <= 180:
        raise ValueError("Longitude must be between -180 and 180")


def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def fetch_window(lat, lon, half_width):
    params = {
        "map": "/map/nitrogen.map",
        "SERVICE": "WCS",
        "VERSION": "2.0.1",
        "REQUEST": "GetCoverage",
        "COVERAGEID": COVERAGE,
        "FORMAT": "image/tiff",
        "SUBSET": [
            f"long({lon - half_width},{lon + half_width})",
            f"lat({lat - half_width},{lat + half_width})",
        ],
        "SUBSETTINGCRS": "http://www.opengis.net/def/crs/EPSG/0/4326",
        "OUTPUTCRS": "http://www.opengis.net/def/crs/EPSG/0/4326",
    }
    response = requests.get(WCS_URL, params=params, timeout=(10, 60))
    # The server answers 400 ExtentError when the window lies entirely outside
    # SoilGrids coverage (open ocean, Antarctica); that is simply "no data here".
    if response.status_code == 400 and "ExtentError" in response.text:
        return None
    response.raise_for_status()
    if not response.headers.get("content-type", "").startswith("image/tiff"):
        raise RuntimeError(f"SoilGrids WCS returned an unexpected response: {response.text[:200]}")

    with MemoryFile(response.content) as memfile, memfile.open() as src:
        return src.read(1), src.transform


def nearest_valid(values, transform, lat, lon):
    # The WCS output has no nodata flag; masked cells come back as 0.
    rows, cols = np.nonzero(values > 0)
    if rows.size == 0:
        return None
    xs, ys = xy(transform, rows, cols)
    distances = haversine_km(lat, lon, np.asarray(ys), np.asarray(xs))
    i = int(np.argmin(distances))
    return {
        "nitrogen_g_kg": round(float(values[rows[i], cols[i]]) / UNIT_DIVISOR, 2),
        "sampled_lat": round(float(ys[i]), 5),
        "sampled_lon": round(float(xs[i]), 5),
        "distance_km": round(float(distances[i]), 2),
    }


def get_nitrogen(lat, lon):
    validate_location(lat, lon)
    for half_width in SEARCH_HALF_WIDTHS_DEG:
        window = fetch_window(lat, lon, half_width)
        if window is None:
            continue
        hit = nearest_valid(*window, lat, lon)
        if hit:
            return {"depth": DEPTH, **hit}

    raise RuntimeError(
        f"No nitrogen data within {SEARCH_HALF_WIDTHS_DEG[-1]} degrees of ({lat}, {lon})."
    )


def save_csv(result, filename="nitrogen_soil.csv"):
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(result.keys()))
        writer.writeheader()
        writer.writerow(result)
    return filename


def main():
    try:
        result = get_nitrogen(LAT, LON)
    except requests.RequestException as error:
        print("API request failed:", error)
        return
    except (RuntimeError, ValueError) as error:
        print("Error:", error)
        return

    if result["distance_km"] > 0.3:
        print(
            f"No data at the exact point - showing nearest 250 m cell with data "
            f"({result['distance_km']} km away at {result['sampled_lat']}, {result['sampled_lon']})"
        )
    print(f"Nitrogen ({DEPTH}): {result['nitrogen_g_kg']} g/kg")
    print(f"\nSaved: {save_csv(result)}")


if __name__ == "__main__":
    main()
