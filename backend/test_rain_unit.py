from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

import rain


def constant_readings(lat, lon, start, end):
    return {start + timedelta(days=i): 2.0 for i in range((end - start).days + 1)}


def test_past_year_has_no_extra_day():
    with patch.object(rain, "query_rainfall", side_effect=constant_readings):
        result = rain.get_annual_precipitation(32, 35, today=date(2026, 11, 14))
    assert result["start_date"] == "2025-11-10"
    assert result["end_date"] == "2026-11-09"
    assert result["days_counted"] == 365
    assert result["total_rainfall_mm"] == 730
    assert sum(month["days_counted"] for month in result["monthly"]) == 365


def test_past_year_includes_leap_day():
    with patch.object(rain, "query_rainfall", side_effect=constant_readings):
        result = rain.get_annual_precipitation(32, 35, today=date(2024, 3, 6))
    assert result["days_counted"] == 366
    assert result["total_rainfall_mm"] == 732


@pytest.mark.parametrize("period", ["past", "next"])
def test_incomplete_archive_is_not_reported_as_full_year(period):
    with patch.object(rain, "query_rainfall", return_value={}):
        with pytest.raises(RuntimeError, match="Incomplete rainfall data"):
            rain.get_annual_precipitation(32, 35, period, today=date(2026, 11, 14))


def test_next_year_is_labeled_estimate_and_queries_only_history():
    with patch.object(rain, "query_rainfall", side_effect=constant_readings) as query:
        result = rain.get_annual_precipitation(32, 35, "next", today=date(2026, 11, 14))
    assert query.call_args.args[2:] == (date(2021, 1, 1), date(2025, 12, 31))
    assert result["start_date"] == "2026-11-15"
    assert result["end_date"] == "2027-11-14"
    assert result["days_counted"] == 365
    assert result["total_rainfall_mm"] == 730
    assert result["data_type"] == "historical_average_estimate"
    assert "not a weather forecast" in result["note"]


def test_next_year_respects_seasonal_rainfall():
    def seasonal_readings(lat, lon, start, end):
        return {day: float(day.month) for day in constant_readings(lat, lon, start, end)}
    with patch.object(rain, "query_rainfall", side_effect=seasonal_readings):
        result = rain.get_annual_precipitation(32, 35, "next", today=date(2026, 11, 14))
    january = next(month for month in result["monthly"] if month["month"] == "2027-01")
    assert january["rainfall_mm"] == 31


def test_query_excludes_missing_nonfinite_and_negative_rainfall():
    response = MagicMock()
    response.json.return_value = {"daily": {
        "time": [f"2026-01-{day:02d}" for day in range(1, 7)],
        "rain_sum": [0, None, float("nan"), float("inf"), -1, True],
    }}
    with patch.object(rain.requests, "get", return_value=response) as request:
        readings = rain.query_rainfall(32, 35, date(2026, 1, 1), date(2026, 1, 6))
    assert readings == {date(2026, 1, 1): 0}
    assert request.call_args.kwargs["params"]["daily"] == "rain_sum"


@pytest.mark.parametrize("lat,lon", [(91, 0), (0, 181), (float("nan"), 0)])
def test_invalid_coordinates_fail_before_request(lat, lon):
    with patch.object(rain.requests, "get") as request:
        with pytest.raises(ValueError):
            rain.get_annual_precipitation(lat, lon)
    request.assert_not_called()
