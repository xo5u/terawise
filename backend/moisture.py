import argparse
import math
from datetime import datetime, timedelta, timezone
import requests

API_URL = "https://archive-api.open-meteo.com/v1/archive"


def get_soil_moisture(lat, lon):
  # Use an older date to ensure historical data
  # has finished processing.
  end_date = datetime.now(timezone.utc).date() - timedelta(days=10)

  start_date = end_date - timedelta(days=2)

  params = {
      "latitude": lat,
      "longitude": lon,
      "start_date": start_date.isoformat(),
      "end_date": end_date.isoformat(),
      "hourly": "soil_moisture_0_to_7cm," "soil_moisture_0_to_100cm",
      "models": "era5_land",
      "timezone": "GMT",
  }

  response = requests.get(API_URL, params=params, timeout=30)
  response.raise_for_status()

  data = response.json()
  hourly = data.get("hourly", {})

  times = hourly.get("time", [])
  surface = hourly.get("soil_moisture_0_to_7cm", [])
  rootzone = hourly.get("soil_moisture_0_to_100cm", [])

  # Find latest valid observation
  for i in range(len(times) - 1, -1, -1):
    s = surface[i] if i < len(surface) else None
    r = rootzone[i] if i < len(rootzone) else None

    if (
        isinstance(s, (int, float))
        and isinstance(r, (int, float))
        and math.isfinite(s)
        and math.isfinite(r)
    ):
      return {
          "date": times[i],
          "surface": s,
          "rootzone": r,
          "surface_percent": round(s * 100, 2),
          "rootzone_percent": round(r * 100, 2),
      }

  raise RuntimeError("No valid soil moisture data found.")


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--lat", type=float, required=True)
  parser.add_argument("--lon", type=float, required=True)
  args = parser.parse_args()

  if not math.isfinite(args.lat) or not -90 <= args.lat <= 90:
    parser.error("Latitude must be between -90 and 90")

  if not math.isfinite(args.lon) or not -180 <= args.lon <= 180:
    parser.error("Longitude must be between -180 and 180")

  try:
    result = get_soil_moisture(args.lat, args.lon)

    print("Date:", result["date"])
    print("Surface %:", result["surface_percent"])
    print("Root Zone %:", result["rootzone_percent"])

  except requests.RequestException as e:
    print("API request failed:", e)

  except RuntimeError as e:
    print("Error:", e)


if __name__ == "__main__":
  main()