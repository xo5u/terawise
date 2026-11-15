"""Unit tests for the soil moisture reader in moisture.py."""

from unittest.mock import MagicMock, patch

import pytest
import requests

import moisture


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


def test_returns_latest_valid_reading():
    times = ["2026-01-01T00:00", "2026-01-01T01:00", "2026-01-01T02:00"]

    with patch.object(moisture.requests, "get", return_value=_response(times, [0.1, 0.2, None], [0.3, 0.4, None])):
        result = moisture.get_soil_moisture(36.5, -98.5)

    assert result["date"] == "2026-01-01T01:00"
    assert result["surface_percent"] == 20.0
    assert result["rootzone_percent"] == 40.0


def test_raises_when_every_reading_is_missing():
    times = ["2026-01-01T00:00", "2026-01-01T01:00"]

    with patch.object(moisture.requests, "get", return_value=_response(times, [None, None], [None, None])):
        with pytest.raises(RuntimeError, match="No valid soil moisture data"):
            moisture.get_soil_moisture(-65, 35.2544)


def test_partial_readings_are_skipped():
    """A row needs both depths; surface alone is not enough."""
    times = ["2026-01-01T00:00", "2026-01-01T01:00"]

    with patch.object(moisture.requests, "get", return_value=_response(times, [0.1, 0.2], [0.3, None])):
        result = moisture.get_soil_moisture(36.5, -98.5)

    assert result["date"] == "2026-01-01T00:00"


def test_http_errors_propagate():
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.HTTPError("boom")

    with patch.object(moisture.requests, "get", return_value=resp):
        with pytest.raises(requests.HTTPError):
            moisture.get_soil_moisture(0, 0)
