"""Suitability scoring and crop eligibility rules.

S = 0.17*SM + 0.17*T + 0.13*ST + 0.13*NU + 0.11*PH + 0.11*AH + 0.18*WR

Weights come from the database. These rules are application policy, not
scientifically validated universal percentages.
"""

import math

# Demand categories: H is never recommended, L outranks M as a whole category.
DEMAND_EXCLUDED = "H"
DEMAND_PREFERRED = "L"
DEMAND_FALLBACK = "M"

RAINFALL_EFFICIENCY = 0.80
BASELINE_MONTHS = 4
MAX_RESULTS = 3


class MissingData(Exception):
    """A value the rules require is absent, so the crop cannot be scored."""


def normalize_texture(value):
    if value is None:
        return None
    return " ".join(str(value).split()).strip().lower()


def number(value, field):
    if value is None:
        raise MissingData(f"missing {field}")
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise MissingData(f"invalid {field}")
    if not math.isfinite(result):
        raise MissingData(f"invalid {field}")
    return result


def range_score(value, optimum, tol_min, tol_max, field):
    """1.0 at the optimum, linear decay to 0 at the tolerance limits, 0 beyond.

    Both shortage and excess reduce suitability, so this is never a plain
    desired/actual ratio.
    """
    value = number(value, f"measured {field}")
    optimum = number(optimum, f"optimal {field}")
    tol_min = number(tol_min, f"{field} lower tolerance limit")
    tol_max = number(tol_max, f"{field} upper tolerance limit")

    if not tol_min <= optimum <= tol_max:
        raise MissingData(f"{field} tolerance limits do not bracket the optimum")

    if value == optimum:
        return 1.0
    if value <= tol_min or value >= tol_max:
        return 0.0

    if value < optimum:
        span = optimum - tol_min
        return (value - tol_min) / span if span > 0 else 0.0

    span = tol_max - optimum
    return (tol_max - value) / span if span > 0 else 0.0


def water_requirement_l(crop, farm_area_m2, plants=None):
    """Litres needed across the crop's full growth duration.

    The stored requirement is a four-month baseline. Per-plant figures are
    multiplied by the plant count; a depth in mm is litres per square metre and
    is multiplied by the area instead, never by the plant count as well.
    """
    months = number(crop.get("growth_duration_months"), "growth duration")
    if months <= 0:
        raise MissingData("growth duration must be positive")

    per_plant = crop.get("optimal_water_requirement_l_per_plant")
    if per_plant is not None:
        per_plant = number(per_plant, "water requirement")
        if per_plant <= 0:
            raise MissingData("water requirement must be positive")
        if plants is None or plants < 1:
            raise MissingData("plant count required for a per-plant water requirement")
        baseline_l = per_plant * plants
    else:
        depth_mm = number(crop.get("optimal_water_requirement_mm"), "water requirement")
        if depth_mm <= 0:
            raise MissingData("water requirement must be positive")
        baseline_l = depth_mm * farm_area_m2

    growth_multiplier = months / BASELINE_MONTHS
    return baseline_l * growth_multiplier, growth_multiplier


def effective_rainfall_l(rainfall_mm, farm_area_m2):
    return rainfall_mm * farm_area_m2 * RAINFALL_EFFICIENCY


def plant_count(crop, farm_area_m2):
    area_per_plant = number(crop.get("area_per_plant_m2"), "area per plant")
    if area_per_plant <= 0:
        raise MissingData("area per plant must be positive")
    return math.floor(farm_area_m2 / area_per_plant)


def evaluate_crop(crop, env, inputs, weights):
    """Eligibility then scoring for one crop.

    Returns a dict with status: "recommended-eligible", "excluded" or
    "insufficient_data", always with a human-readable reason when not eligible.
    """
    result = {
        "crop_id": crop.get("id"),
        "name": crop.get("name"),
        "demand": crop.get("soil_nutrient_demand"),
        "growth_duration_months": crop.get("growth_duration_months"),
    }

    demand = (crop.get("soil_nutrient_demand") or "").strip().upper()
    if demand == DEMAND_EXCLUDED:
        return {**result, "status": "excluded", "reason": "High nutrient demand crops are never recommended"}
    if demand not in (DEMAND_PREFERRED, DEMAND_FALLBACK):
        return {**result, "status": "insufficient_data", "reason": "Unknown nutrient demand category"}

    # Soil type is categorical: compatibility matching, never division.
    compatible = crop.get("compatible_soil_textures") or ([crop["optimal_soil_texture"]] if crop.get("optimal_soil_texture") else [])
    compatible_norm = {normalize_texture(t) for t in compatible if t}
    if not compatible_norm:
        return {**result, "status": "insufficient_data", "reason": "No compatible soil types configured"}

    farm_texture = normalize_texture(env.get("soil_texture_class"))
    if farm_texture is None:
        return {**result, "status": "insufficient_data", "reason": "Soil type could not be measured for this location"}
    if farm_texture not in compatible_norm:
        return {
            **result,
            "status": "excluded",
            "reason": f"Soil type {env['soil_texture_class']} is not compatible with this crop",
        }

    try:
        count = plant_count(crop, inputs["farm_area_m2"])
    except MissingData as error:
        return {**result, "status": "insufficient_data", "reason": str(error)}

    if count < 1:
        return {**result, "status": "excluded", "reason": "Farm area is too small for even one plant"}

    try:
        required_l, growth_multiplier = water_requirement_l(crop, inputs["farm_area_m2"], count)
    except MissingData as error:
        return {**result, "status": "insufficient_data", "reason": str(error)}

    rainfall = env.get("rainfall_mm_by_crop", {}).get(crop.get("id"))
    if rainfall is None:
        return {**result, "status": "insufficient_data", "reason": "Rainfall data unavailable for this growth period"}

    # Effective rainfall uses the arithmetic mean of the monthly figures across
    # the growth window, not their sum.
    rainfall_mm = rainfall.get("mean_monthly_mm", rainfall["total_mm"])
    rain_l = effective_rainfall_l(rainfall_mm, inputs["farm_area_m2"])
    available_l = inputs["tank_water_l"] + rain_l

    water = {
        "plant_count": count,
        "growth_multiplier": round(growth_multiplier, 4),
        "required_water_l": round(required_l, 2),
        "tank_water_l": round(inputs["tank_water_l"], 2),
        "rainfall_mm": round(rainfall_mm, 2),
        "rainfall_total_mm": round(rainfall["total_mm"], 2),
        "effective_rainfall_l": round(rain_l, 2),
        "available_water_l": round(available_l, 2),
        "water_surplus_l": round(available_l - required_l, 2),
        "rainfall_basis": rainfall["basis"],
    }

    if available_l < required_l:
        return {
            **result,
            **water,
            "status": "excluded",
            "reason": "Available water is less than the crop needs over its growth duration",
        }

    # Surviving crops are compatible and have enough water, so ST and WR are 1
    # by construction. Kept explicit rather than hidden.
    factors = {"ST": 1.0, "WR": min(available_l / required_l, 1.0)}

    try:
        factors["SM"] = range_score(
            env.get("soil_moisture_percent"), crop.get("optimal_soil_moisture"),
            crop.get("tol_soil_moisture_min"), crop.get("tol_soil_moisture_max"), "soil moisture",
        )
        factors["T"] = range_score(
            rainfall["mean_temperature_c"], crop.get("optimal_temperature_c"),
            crop.get("tol_temperature_min_c"), crop.get("tol_temperature_max_c"), "temperature",
        )
        factors["NU"] = range_score(
            env.get("nitrogen_g_kg"), crop.get("optimal_nutrients"),
            crop.get("tol_nutrients_min"), crop.get("tol_nutrients_max"), "nitrogen",
        )
        factors["PH"] = range_score(
            env.get("ph"), crop.get("optimal_ph"),
            crop.get("tol_ph_min"), crop.get("tol_ph_max"), "pH",
        )
        factors["AH"] = range_score(
            rainfall["mean_humidity_percent"], crop.get("optimal_humidity"),
            crop.get("tol_humidity_min"), crop.get("tol_humidity_max"), "air humidity",
        )
    except MissingData as error:
        return {**result, **water, "status": "insufficient_data", "reason": str(error)}

    score = sum(weights[factor] * value for factor, value in factors.items())

    return {
        **result,
        **water,
        "status": "eligible",
        "reason": None,
        "factors": {k: round(v, 4) for k, v in factors.items()},
        "suitability": round(score, 4),
        "suitability_percent": round(score * 100, 1),
    }


def rank(evaluations):
    """Rank eligible crops: all L first; M only when no eligible L exists."""
    eligible = [e for e in evaluations if e["status"] == "eligible"]

    preferred = [e for e in eligible if (e["demand"] or "").upper() == DEMAND_PREFERRED]
    fallback = [e for e in eligible if (e["demand"] or "").upper() == DEMAND_FALLBACK]

    # M crops are a fallback for the whole category, never a backfill alongside L.
    selected = preferred if preferred else fallback
    category = DEMAND_PREFERRED if preferred else (DEMAND_FALLBACK if fallback else None)

    selected = sorted(selected, key=lambda e: e["suitability"], reverse=True)[:MAX_RESULTS]
    return selected, category
