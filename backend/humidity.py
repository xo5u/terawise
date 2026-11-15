import cdsapi
import xarray as xr
import math
import os
import sys
import csv
from datetime import datetime

# ==========================================
# 1. HARDCODED API CONFIGURATION
# ==========================================

API_URL = "https://cds.climate.copernicus.eu/api"

# Paste the CDS token you generated here
API_KEY = "b0e0cf27-6b51-4d84-8259-981649e486bb"

# ==========================================
# 2. LOCATION
# ==========================================

LAT = 32.2211
LON = 35.2544

# ==========================================
# 3. DATE AND TIME (UTC)
# ==========================================

YEAR = 2025
MONTH = 6
DAY = 15
HOUR = 12

OUTPUT_FILE = "era5_humidity.nc"
CSV_FILE = "era5_humidity_log.csv"

# ==========================================
# 4. VALIDATE SETTINGS
# ==========================================

try:
    datetime(YEAR, MONTH, DAY, HOUR)
except ValueError as e:
    sys.exit(f"Invalid date: {e}")

if not -90 <= LAT <= 90:
    sys.exit("Invalid latitude")

if not -180 <= LON <= 180:
    sys.exit("Invalid longitude")

if API_KEY == "YOUR_CDS_API_TOKEN":
    sys.exit("Please enter your CDS API token")

# ==========================================
# 5. CONNECT TO COPERNICUS
# ==========================================

try:
    client = cdsapi.Client(
        url=API_URL,
        key=API_KEY,
        quiet=True,
        timeout=120
    )
except Exception as e:
    sys.exit(f"Connection error: {e}")

# ==========================================
# 6. PREPARE ERA5 REQUEST
# ==========================================

# Small bounding box around coordinates
north = min(90, LAT + 0.25)
south = max(-90, LAT - 0.25)
west = max(-180, LON - 0.25)
east = min(180, LON + 0.25)

request = {
    "product_type": ["reanalysis"],
    "variable": [
        "2m_temperature",
        "2m_dewpoint_temperature"
    ],
    "year": [str(YEAR)],
    "month": [f"{MONTH:02d}"],
    "day": [f"{DAY:02d}"],
    "time": [f"{HOUR:02d}:00"],
    "data_format": "netcdf",
    "download_format": "unarchived",
    "area": [
        north,
        west,
        south,
        east
    ]
}

# ==========================================
# 7. DOWNLOAD ERA5 DATA
# ==========================================

try:
    # Remove previous download to avoid
    # accidentally reading old data.
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)

    client.retrieve(
        "reanalysis-era5-single-levels",
        request,
        OUTPUT_FILE
    )
except Exception as e:
    error = str(e)

    if "401" in error:
        sys.exit(
            "ERROR 401: Authentication failed.\n"
            "Check your API token and ERA5 licence."
        )
    elif "405" in error:
        sys.exit(
            "ERROR 405: Method Not Allowed.\n"
            "Update cdsapi and verify the API URL.\n"
            f"Details: {error}"
        )
    elif "403" in error:
        sys.exit(
            "ERROR 403: Access forbidden.\n"
            "Check dataset licence acceptance."
        )
    else:
        sys.exit(f"Download failed: {error}")

# ==========================================
# 8. READ ERA5 NETCDF DATA
# ==========================================

try:
    with xr.open_dataset(OUTPUT_FILE) as ds:
        lat_name = (
            "latitude"
            if "latitude" in ds.coords
            else "lat"
        )
        lon_name = (
            "longitude"
            if "longitude" in ds.coords
            else "lon"
        )

        # ERA5 grid values, nearest location
        point = ds.sel(
            {
                lat_name: LAT,
                lon_name: LON
            },
            method="nearest"
        )

        # Convert Kelvin to Celsius
        temp = (
            float(point["t2m"].values.squeeze())
            - 273.15
        )

        dewpoint = (
            float(point["d2m"].values.squeeze())
            - 273.15
        )

        # ==================================
        # 9. CALCULATE RELATIVE HUMIDITY
        # ==================================

        def saturation_pressure(t):
            return 6.112 * math.exp(
                17.67 * t / (t + 243.5)
            )

        humidity = (
            100.0
            - saturation_pressure(dewpoint)
            / saturation_pressure(temp)
        )

        humidity = max(
            0.0,
            min(100.0, humidity)
        )

        final_humidity = round(humidity, 2)
        final_temp = round(temp, 2)
        final_dewpoint = round(dewpoint, 2)
        timestamp_str = f"{YEAR}-{MONTH:02d}-{DAY:02d} {HOUR:02d}:00"

        # ==================================
        # 10. PRINT AND SAVE TO CSV
        # ==================================

        print(final_humidity)

        file_exists = os.path.exists(CSV_FILE)

        with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Latitude", "Longitude", "Temperature_C", "Dewpoint_C", "Humidity_Percent"])
            
            # Write data row
            writer.writerow([timestamp_str, LAT, LON, final_temp, final_dewpoint, final_humidity])

except Exception as e:
    sys.exit(f"Processing error: {e}")