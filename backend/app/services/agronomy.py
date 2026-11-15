"""Gathers environment readings and assembles crop recommendations."""

import calendar
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path
from statistics import mean

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import moisture
import nitrogen as nitrogen_source
import pH as ph_source
import rain
import soil_texture as texture_source
import temp as temperature_source

from app.services import crops_repo
from app.services.scoring import MissingData, evaluate_crop, rank

BASELINE_YEARS = 5


def month_sequence(start_year, start_month, count):
    year, month = start_year, start_month
    for _ in range(count):
        yield year, month
        month += 1
        if month > 12:
            month = 1
            year += 1


def rainfall_climatology(lat, lon, today=None):
    """Mean rainfall per calendar month (mm) over the last 5 complete years."""
    today = today or date.today()
    last_year = today.year - 1
    start = date(last_year - BASELINE_YEARS + 1, 1, 1)
    end = date(last_year, 12, 31)

    readings = rain.query_rainfall(lat, lon, start, end)
    if not readings:
        raise RuntimeError("No rainfall history available for this location")

    totals = {month: [] for month in range(1, 13)}
    for day, value in readings.items():
        totals[day.month].append((day.year, value))

    monthly = {}
    for month, samples in totals.items():
        if not samples:
            continue
        per_year = {}
        for year, value in samples:
            per_year[year] = per_year.get(year, 0.0) + value
        monthly[month] = mean(per_year.values())
    return monthly


def gather_environment(lat, lon):
    """Point measurements plus monthly climate profiles, each isolated from the others."""

    def safe(name, fn):
        try:
            return name, {"value": fn(), "error": None}
        except Exception as error:
            return name, {"value": None, "error": f"{type(error).__name__}: {error}"}

    # Every reading is fetched fresh on each request; nothing is reused.
    jobs = {
        "moisture": lambda: moisture.get_soil_moisture(lat, lon),
        "nitrogen": lambda: nitrogen_source.get_nitrogen(lat, lon),
        "ph": lambda: ph_source.to_rows(ph_source.get_soil_ph(lat, lon)),
        "texture": lambda: texture_source.get_soil_texture(lat, lon),
        "climate": lambda: temperature_source.monthly_climate(lat, lon),
        "rainfall": lambda: rainfall_climatology(lat, lon),
    }

    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        results = dict(pool.map(lambda item: safe(*item), jobs.items()))

    ph_rows = results["ph"]["value"] or []
    surface_ph = None
    ph_source_name = "USDA soil survey"
    if ph_rows:
        try:
            surface_ph = float(ph_rows[0]["ph"])
        except (TypeError, ValueError, KeyError):
            surface_ph = None

    # The USDA survey has gaps and stops at the US border; SoilGrids covers both.
    if surface_ph is None:
        try:
            surface_ph = texture_source.get_ph(lat, lon)["ph"]
            ph_source_name = "SoilGrids"
            results["ph"]["error"] = None
        except Exception as error:
            results["ph"]["error"] = f"{type(error).__name__}: {error}"

    moisture_reading = results["moisture"]["value"]
    nitrogen_reading = results["nitrogen"]["value"]
    texture_reading = results["texture"]["value"]

    return {
        "soil_moisture_percent": moisture_reading["surface_percent"] if moisture_reading else None,
        "nitrogen_g_kg": nitrogen_reading["nitrogen_g_kg"] if nitrogen_reading else None,
        "ph": surface_ph,
        "ph_source": ph_source_name,
        "soil_rows": ph_rows,
        "soil_texture_class": texture_reading["texture_class"] if texture_reading else None,
        "soil_texture": texture_reading,
        "monthly_climate": results["climate"]["value"] or {},
        "monthly_rainfall_mm": results["rainfall"]["value"] or {},
        "sources": {name: results[name]["error"] for name in results},
    }


def growth_window(env, planting_date, months, today=None):
    """Totals across the crop's growth duration, from monthly climate profiles."""
    months = int(round(months))
    climate = env["monthly_climate"]
    rainfall = env["monthly_rainfall_mm"]
    if not climate or not rainfall:
        return None

    today = today or date.today()
    temperatures, humidities, rain_total, per_month = [], [], 0.0, []

    for year, month in month_sequence(planting_date.year, planting_date.month, months):
        month_climate = climate.get(month)
        month_rain = rainfall.get(month)
        if month_climate is None or month_rain is None:
            return None

        temperatures.append(month_climate["temperature_c"])
        if month_climate["humidity_percent"] is not None:
            humidities.append(month_climate["humidity_percent"])
        rain_total += month_rain
        per_month.append({
            "month": f"{year}-{month:02d}",
            "rainfall_mm": round(month_rain, 2),
            "mean_temperature_c": month_climate["temperature_c"],
            "mean_humidity_percent": month_climate["humidity_percent"],
        })

    # Climatology, not a forecast: the label travels with the numbers.
    first = date(planting_date.year, planting_date.month, 1)
    basis = "historical_average_estimate" if first >= today.replace(day=1) else "historical_average"

    return {
        "total_mm": rain_total,
        # Arithmetic mean of the monthly figures across the growth window.
        "mean_monthly_mm": rain_total / len(per_month) if per_month else 0.0,
        "mean_temperature_c": mean(temperatures) if temperatures else None,
        "mean_humidity_percent": mean(humidities) if humidities else None,
        "months": per_month,
        "basis": basis,
    }


def harvest_date(planting_date, months):
    months = int(round(months))
    year = planting_date.year + (planting_date.month - 1 + months) // 12
    month = (planting_date.month - 1 + months) % 12 + 1
    day = min(planting_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def fertilizer_plan(crop, env, fertilizers):
    """Nitrogen shortfall and the fertilizer needed to cover it."""
    optimal = crop.get("optimal_nutrients")
    available = env.get("nitrogen_g_kg")
    if optimal is None or available is None:
        return {"status": "unavailable", "reason": "Nitrogen reading or crop requirement missing"}

    deficit = max(0.0, float(optimal) - float(available))
    if deficit == 0:
        return {
            "status": "sufficient",
            "nitrogen_deficit_g_per_kg": 0.0,
            "required_fertilizer": None,
            "reason": "Measured nitrogen already meets the crop requirement",
        }

    # The reading is total soil nitrogen as a concentration (g/kg) and the crop
    # requirement carries no documented unit or soil basis. Converting a
    # concentration gap into a mass for the farm needs soil bulk density and an
    # incorporation depth, neither of which is stored, so no mass is invented.
    options = [
        {
            "product_name": f.get("product_name"),
            "manufacturer": f.get("manufacturer"),
            # Stored as a fraction (0.05 = 5%), so it is not divided by 100 again.
            "nitrogen_percent": round(float(f["nitrogen"]) * 100, 2),
        }
        for f in fertilizers
        if f.get("nitrogen") not in (None, "") and float(f["nitrogen"]) > 0
    ]

    return {
        "status": "cannot_calculate",
        "nitrogen_deficit_g_per_kg": round(deficit, 3),
        "required_fertilizer": None,
        "reason": (
            "Cannot convert a soil nitrogen concentration (g/kg) into a fertilizer mass "
            "without soil bulk density and incorporation depth, and crops.optimal_nutrients "
            "has no documented unit or soil basis."
        ),
        "available_products": options,
    }


def timeline(crop, planting_date, window, required_water_l, months):
    """Month-by-month view from planting to expected harvest."""
    months = int(round(months))
    if not window or months < 1:
        return []

    per_month_l = required_water_l / months
    rows = []
    for entry in window["months"]:
        rows.append({
            "month": entry["month"],
            "estimated_water_demand_l": round(per_month_l, 2),
            "rainfall_mm": entry["rainfall_mm"],
            "mean_temperature_c": entry["mean_temperature_c"],
            "estimate": True,
        })
    return rows


def recommend(lat, lon, farm_area_m2, tank_water_l, planting_date, user_id=None):
    weights = crops_repo.get_weights()
    crops = crops_repo.get_crops()
    fertilizers = crops_repo.get_fertilizers()

    env = gather_environment(lat, lon)

    # One growth window per distinct duration, shared by crops of that length.
    windows = {}
    rainfall_by_crop = {}
    for crop in crops:
        months = crop.get("growth_duration_months")
        if months in (None, ""):
            continue
        months = int(round(float(months)))
        if months not in windows:
            windows[months] = growth_window(env, planting_date, months)
        if windows[months]:
            rainfall_by_crop[crop["id"]] = windows[months]

    env["rainfall_mm_by_crop"] = rainfall_by_crop
    inputs = {"farm_area_m2": farm_area_m2, "tank_water_l": tank_water_l}

    evaluations = [evaluate_crop(crop, env, inputs, weights) for crop in crops]
    by_id = {crop["id"]: crop for crop in crops}
    selected, category = rank(evaluations)

    for entry in selected:
        crop = by_id[entry["crop_id"]]
        months = int(round(float(crop["growth_duration_months"])))
        window = windows.get(months)
        entry["expected_harvest"] = harvest_date(planting_date, months).isoformat()
        entry["fertilizer"] = fertilizer_plan(crop, env, fertilizers)
        entry["timeline"] = timeline(crop, planting_date, window, entry["required_water_l"], months)

    # Crops that only failed the water check, nearest first, so the page can say
    # how much more water would qualify them instead of just "nothing matched".
    water_short = sorted(
        (
            e for e in evaluations
            if e["status"] == "excluded"
            and e.get("water_surplus_l") is not None
            and e["water_surplus_l"] < 0
        ),
        key=lambda e: e["water_surplus_l"],
        reverse=True,
    )[:3]

    shortfalls = [
        {
            "name": e["name"],
            "demand": e["demand"],
            "required_water_l": e["required_water_l"],
            "available_water_l": e["available_water_l"],
            "additional_water_needed_l": round(-e["water_surplus_l"], 2),
        }
        for e in water_short
    ]

    history = []
    try:
        history = crops_repo.get_history(user_id) if user_id else []
    except Exception:
        history = []

    return {
        "location": {"lat": lat, "lon": lon},
        "inputs": {
            "farm_area_m2": farm_area_m2,
            "tank_water_l": tank_water_l,
            "planting_date": planting_date.isoformat(),
        },
        "environment": {
            "soil_moisture_percent": env["soil_moisture_percent"],
            "soil_texture_class": env["soil_texture_class"],
            "soil_texture": env["soil_texture"],
            "nitrogen_g_kg": env["nitrogen_g_kg"],
            "ph": env["ph"],
            "ph_source": env["ph_source"],
            "soil_layers": env["soil_rows"],
            "source_errors": {k: v for k, v in env["sources"].items() if v},
        },
        "weights": weights,
        "selected_category": category,
        "recommendations": selected,
        "water_shortfalls": shortfalls,
        "excluded": [e for e in evaluations if e["status"] == "excluded"],
        "insufficient_data": [e for e in evaluations if e["status"] == "insufficient_data"],
        "recent_history": history[:2],
        "history": history,
    }
