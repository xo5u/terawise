"""Soil texture class for a point, from SoilGrids sand/silt/clay fractions.

Returns a USDA texture class, so crops can be matched on a normalized soil
identifier rather than on free-text soil survey names.
"""

from concurrent.futures import ThreadPoolExecutor

import requests

from nitrogen import SEARCH_HALF_WIDTHS_DEG, fetch_window, nearest_valid, validate_location

FRACTIONS = ("sand", "silt", "clay")
DEPTH = "0-5cm"


def usda_texture_class(sand, silt, clay):
    """Classify percentages (summing to 100) using the USDA texture triangle."""
    if silt + 1.5 * clay < 15:
        return "Sand"
    if silt + 1.5 * clay < 30:
        return "Loamy Sand"
    if (7 <= clay < 20 and sand > 52 and silt + 2 * clay >= 30) or (clay < 7 and silt < 50):
        return "Sandy Loam"
    if 7 <= clay < 27 and 28 <= silt < 50 and sand <= 52:
        return "Loam"
    if silt >= 50 and 12 <= clay < 27:
        return "Silt Loam"
    if 50 <= silt < 80 and clay < 12:
        return "Silt Loam"
    if silt >= 80 and clay < 12:
        return "Silt"
    if 20 <= clay < 35 and silt < 28 and sand > 45:
        return "Sandy Clay Loam"
    if 27 <= clay < 40 and 20 < sand <= 45:
        return "Clay Loam"
    if 27 <= clay < 40 and sand <= 20:
        return "Silty Clay Loam"
    if clay >= 35 and sand > 45:
        return "Sandy Clay"
    if clay >= 40 and silt >= 40:
        return "Silty Clay"
    return "Clay"


def fetch_property(lat, lon, prop):
    """Raw SoilGrids value for a property at or near the point."""
    for half_width in SEARCH_HALF_WIDTHS_DEG:
        window = fetch_window(
            lat,
            lon,
            half_width,
            map_name=f"/map/{prop}.map",
            coverage=f"{prop}_0-5cm_mean",
        )
        if window is None:
            continue
        hit = nearest_valid(*window, lat, lon)
        if hit:
            # nearest_valid scales to nitrogen units; undo that for the raw value.
            return hit["nitrogen_g_kg"] * 100, hit["distance_km"]
    return None, None


def fetch_fraction(lat, lon, fraction):
    """Mean value of one particle-size fraction, in g/kg, at or near the point."""
    return fetch_property(lat, lon, fraction)


def get_ph(lat, lon):
    """Topsoil pH from SoilGrids, which stores it as pH x 10.

    Used where the USDA soil survey has no record for the point, and anywhere
    outside the United States.
    """
    validate_location(lat, lon)
    raw, distance = fetch_property(lat, lon, "phh2o")
    if raw is None:
        raise RuntimeError(f"No soil pH data available for ({lat}, {lon}).")
    return {
        "ph": round(raw / 10, 2),
        "distance_km": round(distance or 0.0, 2),
        "source": "SoilGrids",
    }


def get_soil_texture(lat, lon):
    validate_location(lat, lon)

    # The three fractions are one logical lookup, so fetch them together rather
    # than paying the round trip three times in a row.
    with ThreadPoolExecutor(max_workers=len(FRACTIONS)) as pool:
        results = dict(
            zip(FRACTIONS, pool.map(lambda f: fetch_fraction(lat, lon, f), FRACTIONS))
        )

    values = {}
    distance = 0.0
    for fraction in FRACTIONS:
        value, dist = results[fraction]
        if value is None:
            raise RuntimeError(f"No {fraction} data available for ({lat}, {lon}).")
        values[fraction] = value
        distance = max(distance, dist or 0.0)

    total = sum(values.values())
    if total <= 0:
        raise RuntimeError(f"Invalid soil texture fractions at ({lat}, {lon}).")

    percentages = {name: value / total * 100 for name, value in values.items()}
    texture = usda_texture_class(percentages["sand"], percentages["silt"], percentages["clay"])

    return {
        "texture_class": texture,
        "sand_percent": round(percentages["sand"], 1),
        "silt_percent": round(percentages["silt"], 1),
        "clay_percent": round(percentages["clay"], 1),
        "depth": DEPTH,
        "distance_km": round(distance, 2),
    }


def main():
    try:
        print(get_soil_texture(32.2211, 35.2544))
    except (requests.RequestException, RuntimeError, ValueError) as error:
        print("Error:", error)


if __name__ == "__main__":
    main()
