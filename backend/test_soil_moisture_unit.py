
import math
import sys
from datetime import date
from unittest.mock import patch, MagicMock

import pytest
import requests

import test as sm


def _response(times, surface, rootzone):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "hourly": {
            "time": times,
            "soil_moisture_0_to_7cm": surface,
            "soil_moisture_0_to_100cm": rootzone,
        }
    }
    return resp


def test_query_window_picks_latest_valid_entry():
    times = ["2026-01-01T00:00", "2026-01-01T01:00", "2026-01-01T02:00"]
    surface = [0.1, 0.2, None]
    rootzone = [0.3, 0.4, None]

    with patch.object(sm.requests, "get", return_value=_response(times, surface, rootzone)):
        result = sm.query_window(36.5, -98.5, date(2026, 1, 1), date(2026, 1, 1))

    assert result["date"] == "2026-01-01T01:00"
    assert result["surface"] == 0.2
    assert result["rootzone"] == 0.4
    assert result["surface_percent"] == 20.0
    assert result["rootzone_percent"] == 40.0


def test_query_window_returns_none_when_all_missing():
    times = ["2026-01-01T00:00", "2026-01-01T01:00"]
    surface = [None, None]
    rootzone = [None, None]

    with patch.object(sm.requests, "get", return_value=_response(times, surface, rootzone)):
        result = sm.query_window(-65, 35.2544, date(2026, 1, 1), date(2026, 1, 1))

    assert result is None


def test_query_window_raises_on_http_error():
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.HTTPError("boom")

    with patch.object(sm.requests, "get", return_value=resp):
        with pytest.raises(requests.HTTPError):
            sm.query_window(0, 0, date(2026, 1, 1), date(2026, 1, 1))


def test_haversine_known_distance():
    # London to Paris, roughly 344 km apart.
    d = sm.haversine_km(51.5074, -0.1278, 48.8566, 2.3522)
    assert 330 < d < 360


def test_haversine_same_point_is_zero():
    assert sm.haversine_km(10, 10, 10, 10) == pytest.approx(0.0)


def test_ring_offsets_has_eight_points_at_radius():
    offsets = list(sm.ring_offsets(2.0))
    assert len(offsets) == 8
    for dlat, dlon in offsets:
        assert math.hypot(dlat, dlon) == pytest.approx(2.0)


def test_clamp_latlon_clamps_latitude():
    lat, lon = sm.clamp_latlon(95, 10)
    assert lat == 90
    assert lon == 10

    lat, lon = sm.clamp_latlon(-95, 10)
    assert lat == -90


def test_clamp_latlon_wraps_longitude():
    lat, lon = sm.clamp_latlon(0, 185)
    assert lon == pytest.approx(-175)

    lat, lon = sm.clamp_latlon(0, -185)
    assert lon == pytest.approx(175)


def test_get_soil_moisture_succeeds_on_first_try():
    hit = {"date": "d", "surface": 0.1, "rootzone": 0.2,
           "surface_percent": 10.0, "rootzone_percent": 20.0}

    with patch.object(sm, "query_window", return_value=dict(hit)) as mock_query:
        result = sm.get_soil_moisture(36.5, -98.5)

    assert mock_query.call_count == 1
    assert result["distance_km"] == 0.0
    assert result["lat"] == 36.5
    assert result["lon"] == -98.5


def test_get_soil_moisture_falls_back_to_wider_date_range():
    hit = {"date": "d", "surface": 0.1, "rootzone": 0.2,
           "surface_percent": 10.0, "rootzone_percent": 20.0}

    with patch.object(sm, "query_window", side_effect=[None, dict(hit)]) as mock_query:
        result = sm.get_soil_moisture(36.5, -98.5)

    assert mock_query.call_count == 2
    assert result["distance_km"] == 0.0


def test_get_soil_moisture_falls_back_to_nearest_point():
    hit = {"date": "d", "surface": 0.1, "rootzone": 0.2,
           "surface_percent": 10.0, "rootzone_percent": 20.0}

    # First two calls (exact point, narrow then wide date range) miss,
    # then the third call (first ring candidate) hits.
    with patch.object(sm, "query_window", side_effect=[None, None, dict(hit)]):
        result = sm.get_soil_moisture(-65, 35.2544)

    assert result["distance_km"] > 0
    assert result["lat"] != -65 or result["lon"] != 35.2544


def test_get_soil_moisture_raises_when_nothing_found_anywhere():
    with patch.object(sm, "query_window", return_value=None):
        with pytest.raises(RuntimeError, match="No valid soil moisture data found"):
            sm.get_soil_moisture(-65, 35.2544)


def test_main_prints_result(monkeypatch, capsys):
    result = {"date": "2026-01-01T00:00", "surface": 0.1, "rootzone": 0.2,
              "surface_percent": 10.0, "rootzone_percent": 20.0,
              "lat": 36.5, "lon": -98.5, "distance_km": 0.0}

    monkeypatch.setattr(sm, "get_soil_moisture", lambda lat, lon: result)
    monkeypatch.setattr(sys, "argv", ["test.py", "--lat", "36.5", "--lon", "-98.5"])

    sm.main()

    out = capsys.readouterr().out
    assert "Surface %: 10.0" in out
    assert "Root Zone %: 20.0" in out
    assert "nearest location" not in out


def test_main_prints_nearest_location_note(monkeypatch, capsys):
    result = {"date": "2026-01-01T00:00", "surface": 0.1, "rootzone": 0.2,
              "surface_percent": 10.0, "rootzone_percent": 20.0,
              "lat": -69.0, "lon": 35.2544, "distance_km": 444.8}

    monkeypatch.setattr(sm, "get_soil_moisture", lambda lat, lon: result)
    monkeypatch.setattr(sys, "argv", ["test.py", "--lat", "-65", "--lon", "35.2544"])

    sm.main()

    out = capsys.readouterr().out
    assert "No data at the exact point" in out
    assert "444.8 km away" in out



def test_main_handles_api_request_error(monkeypatch, capsys):
    def boom(lat, lon):
        raise requests.RequestException("network down")

    monkeypatch.setattr(sm, "get_soil_moisture", boom)
    monkeypatch.setattr(sys, "argv", ["test.py", "--lat", "36.5", "--lon", "-98.5"])

    sm.main()

    out = capsys.readouterr().out
    assert "API request failed:" in out


def test_main_handles_runtime_error(monkeypatch, capsys):
    def boom(lat, lon):
        raise RuntimeError("No valid soil moisture data found.")

    monkeypatch.setattr(sm, "get_soil_moisture", boom)
    monkeypatch.setattr(sys, "argv", ["test.py", "--lat", "36.5", "--lon", "-98.5"])

    sm.main()

    out = capsys.readouterr().out
    assert "Error:" in out


def test_main_rejects_invalid_latitude(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["test.py", "--lat", "999", "--lon", "0"])

    with pytest.raises(SystemExit):
        sm.main()

    err = capsys.readouterr().err
    assert "Latitude must be between -90 and 90" in err


def test_main_rejects_invalid_longitude(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["test.py", "--lat", "0", "--lon", "999"])

    with pytest.raises(SystemExit):
        sm.main()

    err = capsys.readouterr().err
    assert "Longitude must be between -180 and 180" in err
