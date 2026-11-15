"""Application defaults for values the crops table does not store.

The weights are fixed application rules applied to every eligible crop. The
per-crop defaults below fill gaps only: any column present in the database wins,
so these can be overridden per crop by adding the columns (see
backend/migrations/001_crop_recommendation.sql).

These are application policy, not scientifically validated figures.
"""

# S = 0.17*SM + 0.17*T + 0.13*ST + 0.13*NU + 0.11*PH + 0.11*AH + 0.18*WR
WEIGHTS = {
    "SM": 0.17,
    "T": 0.17,
    "ST": 0.13,
    "NU": 0.13,
    "PH": 0.11,
    "AH": 0.11,
    "WR": 0.18,
}

# Symmetric tolerance band around each optimum: (column prefix, optimum column,
# band, floor, ceiling). Score falls linearly from 1 at the optimum to 0 here.
TOLERANCE_BANDS = (
    ("tol_temperature_min_c", "tol_temperature_max_c", "optimal_temperature_c", 10, None, None),
    ("tol_soil_moisture_min", "tol_soil_moisture_max", "optimal_soil_moisture", 12.5, 0, None),
    ("tol_ph_min", "tol_ph_max", "optimal_ph", 1.5, 0, 14),
    ("tol_humidity_min", "tol_humidity_max", "optimal_humidity", 25, 0, 100),
    ("tol_nutrients_min", "tol_nutrients_max", "optimal_nutrients", 0.8, 0, None),
)

# Ground area one plant occupies, in square metres.
AREA_PER_PLANT_M2 = {
    "Apple": 20, "Orange": 20, "Peach": 20, "Pear": 20, "Cherry": 25, "Plum": 20,
    "Apricot": 20, "Lemon": 16, "Grapefruit": 20, "Avocado": 25, "Almond": 25,
    "Fig": 20, "Pomegranate": 12, "Grape": 4, "Blueberry": 2.5, "Blackberry": 2,
    "Raspberry": 1.5, "Cranberry": 1, "Pineapple": 0.6, "Watermelon": 3,
    "Cantaloupe": 2, "Zucchini": 1, "Cucumber": 0.5, "Tomato": 0.5,
    "Broccoli": 0.25, "Sweet Corn": 0.25, "Kale": 0.25, "Strawberry": 0.15,
    "Bush Bean": 0.1, "Peas": 0.1, "Mustard Greens": 0.1, "Lettuce": 0.09,
    "Spinach": 0.06, "Beet": 0.02, "Carrot": 0.01, "Radish": 0.01,
}

# Measured soil is classified into a USDA texture class, so each crop needs the
# explicit set of classes it accepts rather than one display name.
#
# Crops listing "Loam" are medium-textured and tolerate heavier ground, so only
# the two coarsest classes are ruled out. Crops listing "Sandy Loam" need free
# drainage, so the three heaviest classes are ruled out instead.
MEDIUM_TEXTURES = [
    "Loam", "Silt Loam", "Silt", "Sandy Loam",
    "Clay Loam", "Silty Clay Loam", "Sandy Clay Loam",
    "Clay", "Silty Clay", "Sandy Clay",
]

FREE_DRAINING_TEXTURES = [
    "Sandy Loam", "Loamy Sand", "Sand", "Loam", "Silt Loam", "Silt",
    "Sandy Clay Loam", "Clay Loam", "Silty Clay Loam",
]

TEXTURE_COMPATIBILITY = {
    "Loam": MEDIUM_TEXTURES,
    "Sandy Loam": FREE_DRAINING_TEXTURES,
}


def _clamp(value, floor, ceiling):
    if floor is not None:
        value = max(value, floor)
    if ceiling is not None:
        value = min(value, ceiling)
    return value


def apply_defaults(crop):
    """Fill gaps in one crop record; stored values always take precedence."""
    crop = dict(crop)

    for min_col, max_col, optimum_col, band, floor, ceiling in TOLERANCE_BANDS:
        optimum = crop.get(optimum_col)
        if optimum is None:
            continue
        optimum = float(optimum)
        if crop.get(min_col) is None:
            crop[min_col] = _clamp(optimum - band, floor, ceiling)
        if crop.get(max_col) is None:
            crop[max_col] = _clamp(optimum + band, floor, ceiling)

    if crop.get("area_per_plant_m2") is None:
        crop["area_per_plant_m2"] = AREA_PER_PLANT_M2.get(crop.get("name"))

    if not crop.get("compatible_soil_textures"):
        texture = crop.get("optimal_soil_texture")
        crop["compatible_soil_textures"] = TEXTURE_COMPATIBILITY.get(
            texture, [texture] if texture else []
        )

    return crop
