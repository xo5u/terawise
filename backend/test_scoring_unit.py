"""Verification cases for the crop recommendation rules (task.md step 10)."""

import pytest

from app.services.scoring import (
    MissingData,
    effective_rainfall_l,
    evaluate_crop,
    plant_count,
    range_score,
    rank,
    water_requirement_l,
)

WEIGHTS = {"SM": 0.17, "T": 0.17, "ST": 0.13, "NU": 0.13, "PH": 0.11, "AH": 0.11, "WR": 0.18}


def make_crop(**overrides):
    crop = {
        "id": overrides.pop("id", "crop-1"),
        "name": "Test Crop",
        "soil_nutrient_demand": "L",
        "growth_duration_months": 4,
        "optimal_soil_texture": "Loam",
        "compatible_soil_textures": ["Loam"],
        "area_per_plant_m2": 1,
        "optimal_water_requirement_mm": 10,
        "optimal_soil_moisture": 27.5,
        "tol_soil_moisture_min": 15,
        "tol_soil_moisture_max": 40,
        "optimal_temperature_c": 20,
        "tol_temperature_min_c": 10,
        "tol_temperature_max_c": 30,
        "optimal_nutrients": 1.5,
        "tol_nutrients_min": 0.7,
        "tol_nutrients_max": 2.3,
        "optimal_ph": 6.5,
        "tol_ph_min": 5.0,
        "tol_ph_max": 8.0,
        "optimal_humidity": 60,
        "tol_humidity_min": 35,
        "tol_humidity_max": 85,
    }
    crop.update(overrides)
    return crop


def make_env(crop_ids=("crop-1",), **overrides):
    window = {
        "total_mm": 0.0,
        "mean_monthly_mm": 0.0,
        "mean_temperature_c": 20,
        "mean_humidity_percent": 60,
        "months": [],
        "basis": "historical_average_estimate",
    }
    window.update(overrides.pop("window", {}))
    env = {
        "soil_moisture_percent": 27.5,
        "nitrogen_g_kg": 1.5,
        "ph": 6.5,
        "soil_texture_class": "Loam",
        "rainfall_mm_by_crop": {cid: window for cid in crop_ids},
    }
    env.update(overrides)
    return env


# --- factor scoring -------------------------------------------------------

def test_score_is_one_at_the_optimum():
    assert range_score(6.5, 6.5, 5.0, 8.0, "pH") == 1.0


def test_score_is_zero_outside_tolerance():
    assert range_score(4.0, 6.5, 5.0, 8.0, "pH") == 0.0
    assert range_score(9.0, 6.5, 5.0, 8.0, "pH") == 0.0


def test_excess_reduces_score_like_shortage():
    below = range_score(5.75, 6.5, 5.0, 8.0, "pH")
    above = range_score(7.25, 6.5, 5.0, 8.0, "pH")
    assert 0 < below < 1 and 0 < above < 1
    # Not a desired/actual ratio: both directions lose suitability.
    assert below == pytest.approx(0.5)
    assert above == pytest.approx(0.5)


def test_missing_tolerance_is_flagged_not_invented():
    with pytest.raises(MissingData, match="tolerance limit"):
        range_score(6.5, 6.5, None, 8.0, "pH")


def test_missing_measurement_is_flagged():
    with pytest.raises(MissingData, match="measured"):
        range_score(None, 6.5, 5.0, 8.0, "pH")


# --- water ----------------------------------------------------------------

def test_thirty_month_crop_scales_by_seven_point_five():
    crop = make_crop(growth_duration_months=30, optimal_water_requirement_mm=10)
    required, multiplier = water_requirement_l(crop, farm_area_m2=100)
    assert multiplier == pytest.approx(7.5)
    # 10 mm over 100 m2 = 1000 L baseline, times 7.5.
    assert required == pytest.approx(7500)


def test_short_crop_scales_proportionally_below_one():
    crop = make_crop(growth_duration_months=2, optimal_water_requirement_mm=10)
    _, multiplier = water_requirement_l(crop, farm_area_m2=100)
    assert multiplier == pytest.approx(0.5)


def test_rainfall_uses_eighty_percent_efficiency():
    assert effective_rainfall_l(rainfall_mm=10, farm_area_m2=100) == pytest.approx(800)


def test_exact_water_equality_passes():
    crop = make_crop(growth_duration_months=4, optimal_water_requirement_mm=1, area_per_plant_m2=1)
    # 1 mm over 55 m2 = 55 L required, multiplier 1.
    result = evaluate_crop(crop, make_env(), {"farm_area_m2": 55, "tank_water_l": 55}, WEIGHTS)
    assert result["status"] == "eligible"
    assert result["required_water_l"] == pytest.approx(55)
    assert result["water_surplus_l"] == pytest.approx(0)


def test_one_litre_short_fails():
    crop = make_crop(growth_duration_months=4, optimal_water_requirement_mm=1)
    result = evaluate_crop(crop, make_env(), {"farm_area_m2": 55, "tank_water_l": 54}, WEIGHTS)
    assert result["status"] == "excluded"
    assert "water" in result["reason"].lower()


def test_three_month_crop_scales_by_exactly_point_seven_five():
    crop = make_crop(growth_duration_months=3, optimal_water_requirement_mm=10)
    required, multiplier = water_requirement_l(crop, farm_area_m2=100)
    assert multiplier == 0.75
    assert required == pytest.approx(750)


def test_one_month_crop_scales_by_a_quarter():
    crop = make_crop(growth_duration_months=1, optimal_water_requirement_mm=10)
    _, multiplier = water_requirement_l(crop, farm_area_m2=100)
    assert multiplier == 0.25


def test_per_plant_requirement_uses_plant_count_not_area():
    crop = make_crop(
        growth_duration_months=3,
        area_per_plant_m2=2,
        optimal_water_requirement_l_per_plant=10,
    )
    crop.pop("optimal_water_requirement_mm", None)
    # 100 m2 / 2 = 50 plants, 50 * 10 L = 500 L baseline, times 0.75.
    required, multiplier = water_requirement_l(crop, farm_area_m2=100, plants=50)
    assert multiplier == 0.75
    assert required == pytest.approx(375)


def test_effective_rainfall_uses_the_monthly_average_not_the_sum():
    crop = make_crop(growth_duration_months=3, optimal_water_requirement_mm=1)
    # Three months totalling 165 mm; the mean of 55 mm is what must be used.
    env = make_env(window={"total_mm": 165.0, "mean_monthly_mm": 55.0})
    result = evaluate_crop(crop, env, {"farm_area_m2": 100, "tank_water_l": 0}, WEIGHTS)
    assert result["rainfall_mm"] == pytest.approx(55.0)
    assert result["effective_rainfall_l"] == pytest.approx(55.0 * 100 * 0.8)
    assert result["rainfall_total_mm"] == pytest.approx(165.0)


def test_rainfall_is_added_to_supply_not_to_requirement():
    crop = make_crop(growth_duration_months=4, optimal_water_requirement_mm=1)
    env = make_env(window={"total_mm": 1.0, "mean_monthly_mm": 1.0})  # 1 mm * 50 m2 * 0.8 = 40 L
    result = evaluate_crop(crop, env, {"farm_area_m2": 50, "tank_water_l": 10}, WEIGHTS)
    assert result["effective_rainfall_l"] == pytest.approx(40)
    assert result["available_water_l"] == pytest.approx(50)
    assert result["required_water_l"] == pytest.approx(50)
    assert result["status"] == "eligible"


# --- eligibility ----------------------------------------------------------

def test_high_demand_crop_is_always_excluded():
    crop = make_crop(soil_nutrient_demand="H")
    result = evaluate_crop(crop, make_env(), {"farm_area_m2": 1000, "tank_water_l": 10**9}, WEIGHTS)
    assert result["status"] == "excluded"
    assert "High nutrient demand" in result["reason"]


def test_incompatible_soil_is_excluded():
    crop = make_crop(compatible_soil_textures=["Sandy Loam"])
    env = make_env(soil_texture_class="Clay")
    result = evaluate_crop(crop, env, {"farm_area_m2": 1000, "tank_water_l": 10**9}, WEIGHTS)
    assert result["status"] == "excluded"
    assert "not compatible" in result["reason"]


def test_soil_match_is_case_and_space_insensitive():
    crop = make_crop(compatible_soil_textures=["sandy  loam"])
    env = make_env(soil_texture_class="Sandy Loam")
    result = evaluate_crop(crop, env, {"farm_area_m2": 1000, "tank_water_l": 10**9}, WEIGHTS)
    assert result["status"] == "eligible"


def test_area_too_small_for_one_plant_is_excluded():
    crop = make_crop(area_per_plant_m2=25)
    result = evaluate_crop(crop, make_env(), {"farm_area_m2": 10, "tank_water_l": 10**9}, WEIGHTS)
    assert result["status"] == "excluded"
    assert "too small" in result["reason"]


def test_plant_count_floors():
    assert plant_count(make_crop(area_per_plant_m2=3), farm_area_m2=10) == 3


def test_missing_api_reading_marks_insufficient_data():
    env = make_env(soil_moisture_percent=None)
    result = evaluate_crop(make_crop(), env, {"farm_area_m2": 1000, "tank_water_l": 10**9}, WEIGHTS)
    assert result["status"] == "insufficient_data"
    assert "soil moisture" in result["reason"]


def test_missing_soil_type_marks_insufficient_data():
    env = make_env(soil_texture_class=None)
    result = evaluate_crop(make_crop(), env, {"farm_area_m2": 1000, "tank_water_l": 10**9}, WEIGHTS)
    assert result["status"] == "insufficient_data"


def test_zero_denominator_is_rejected():
    crop = make_crop(area_per_plant_m2=0)
    result = evaluate_crop(crop, make_env(), {"farm_area_m2": 10, "tank_water_l": 10**9}, WEIGHTS)
    assert result["status"] == "insufficient_data"


def test_surviving_crops_have_st_and_wr_equal_to_one():
    result = evaluate_crop(make_crop(), make_env(), {"farm_area_m2": 1000, "tank_water_l": 10**9}, WEIGHTS)
    assert result["factors"]["ST"] == 1.0
    assert result["factors"]["WR"] == 1.0


def test_perfect_conditions_score_one_hundred_percent():
    result = evaluate_crop(make_crop(), make_env(), {"farm_area_m2": 1000, "tank_water_l": 10**9}, WEIGHTS)
    assert result["suitability_percent"] == pytest.approx(100.0)


# --- ranking --------------------------------------------------------------

def _eligible(name, demand, score):
    return {"name": name, "demand": demand, "status": "eligible", "suitability": score}


def test_low_demand_beats_higher_scoring_medium():
    selected, category = rank([
        _eligible("M crop", "M", 0.99),
        _eligible("L crop", "L", 0.10),
    ])
    assert category == "L"
    assert [c["name"] for c in selected] == ["L crop"]


def test_single_low_demand_crop_is_not_backfilled_with_medium():
    selected, _ = rank([
        _eligible("L crop", "L", 0.5),
        _eligible("M one", "M", 0.9),
        _eligible("M two", "M", 0.8),
    ])
    assert len(selected) == 1


def test_medium_is_used_only_when_no_low_demand_crop_qualifies():
    selected, category = rank([
        _eligible("M one", "M", 0.9),
        _eligible("M two", "M", 0.8),
    ])
    assert category == "M"
    assert [c["name"] for c in selected] == ["M one", "M two"]


def test_at_most_three_results_ordered_by_score():
    selected, _ = rank([_eligible(f"L{i}", "L", i / 10) for i in range(6)])
    assert [c["name"] for c in selected] == ["L5", "L4", "L3"]


def test_high_demand_never_appears_even_if_marked_eligible():
    selected, category = rank([_eligible("H crop", "H", 1.0)])
    assert selected == []
    assert category is None


def test_no_eligible_crops_returns_no_category():
    selected, category = rank([{"status": "excluded", "demand": "L", "name": "x"}])
    assert selected == []
    assert category is None
