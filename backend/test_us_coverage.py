
import requests

import test as sm

# Same bounding box the frontend map restricts picks to.
US_LAT_RANGE = (24.0, 49.5)
US_LON_RANGE = (-125.0, -66.0)
REQUIRED_SUCCESS_RATE = 0.85


def us_grid(lat_steps=6, lon_steps=6):
    lat_lo, lat_hi = US_LAT_RANGE
    lon_lo, lon_hi = US_LON_RANGE
    for i in range(lat_steps):
        lat = lat_lo + (lat_hi - lat_lo) * i / (lat_steps - 1)
        for j in range(lon_steps):
            lon = lon_lo + (lon_hi - lon_lo) * j / (lon_steps - 1)
            yield round(lat, 4), round(lon, 4)


def test_soil_moisture_available_for_most_of_the_us():
    points = list(us_grid())
    failures = []

    for lat, lon in points:
        try:
            sm.get_soil_moisture(lat, lon)
        except requests.RequestException as exc:
            failures.append((lat, lon, f"request failed: {exc}"))
        except RuntimeError as exc:
            failures.append((lat, lon, str(exc)))

    success_rate = (len(points) - len(failures)) / len(points)

    assert success_rate >= REQUIRED_SUCCESS_RATE, (
        f"Only {success_rate:.0%} of {len(points)} sampled US points returned "
        f"soil moisture data (need >= {REQUIRED_SUCCESS_RATE:.0%}). "
        f"Failures: {failures}"
    )
