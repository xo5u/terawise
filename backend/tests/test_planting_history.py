"""Plant selections persist server-owned crop snapshots in planting_history."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from postgrest.exceptions import APIError
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.recommend import router
from app.services import crops_repo
from app.services.history_auth import get_history_user


@pytest.fixture
def api():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_history_user] = lambda: "e937025b-e50c-490c-b42b-ef7619ca4d11"
    return TestClient(app)


@pytest.fixture
def crop():
    return {"id": "crop-1", "name": "Tomato", "soil_nutrient_demand": "H"}


def test_selected_crop_is_saved_with_requested_dates(api, monkeypatch, crop):
    saved = [{"id": "history-1", "plant_name": "Tomato"}]
    monkeypatch.setattr(crops_repo, "get_crops", lambda: [crop])
    insert = Mock(return_value=saved)
    monkeypatch.setattr(crops_repo, "add_history", insert)

    response = api.post("/api/history", json={
        "crop_id": "crop-1", "planting_date": "2026-11-15", "user_id": "e937025b-e50c-490c-b42b-ef7619ca4d11",
        "harvest_date": "2027-03-15",
    })

    assert response.is_success
    assert response.json() == saved
    insert.assert_called_once_with(crop, "2026-11-15", "e937025b-e50c-490c-b42b-ef7619ca4d11", "2027-03-15")


def test_unknown_crop_is_not_inserted(api, monkeypatch):
    monkeypatch.setattr(crops_repo, "get_crops", lambda: [])
    insert = Mock()
    monkeypatch.setattr(crops_repo, "add_history", insert)

    response = api.post("/api/history", json={
        "crop_id": "missing", "planting_date": "2026-11-15", "user_id": "e937025b-e50c-490c-b42b-ef7619ca4d11",
    })

    assert response.status_code == 404
    insert.assert_not_called()


def test_invalid_date_is_rejected_before_database_access(api, monkeypatch):
    read = Mock()
    monkeypatch.setattr(crops_repo, "get_crops", read)
    response = api.post("/api/history", json={
        "crop_id": "crop-1", "planting_date": "2026-02-30", "user_id": "e937025b-e50c-490c-b42b-ef7619ca4d11",
    })
    assert response.status_code == 422
    read.assert_not_called()


def test_missing_session_is_rejected_before_inserting(monkeypatch):
    app = FastAPI()
    app.include_router(router)
    api = TestClient(app)
    insert = Mock()
    monkeypatch.setattr(crops_repo, "add_history", insert)
    response = api.post("/api/history", json={
        "crop_id": "crop-1", "planting_date": "2026-11-15",
    })
    assert response.status_code == 401
    insert.assert_not_called()


def test_history_is_scoped_to_session_not_query_string(api, monkeypatch):
    read = Mock(return_value=[])
    monkeypatch.setattr(crops_repo, "get_history", read)
    response = api.get("/api/history?user_id=00000000-0000-0000-0000-000000000001")
    assert response.status_code == 200
    read.assert_called_once_with("e937025b-e50c-490c-b42b-ef7619ca4d11")


def test_client_cannot_override_owner(api, monkeypatch, crop):
    monkeypatch.setattr(crops_repo, "get_crops", lambda: [crop])
    insert = Mock(return_value=[{"id": "history-1"}])
    monkeypatch.setattr(crops_repo, "add_history", insert)
    response = api.post("/api/history", json={
        "crop_id": "crop-1", "planting_date": "2026-11-15",
        "user_id": "00000000-0000-0000-0000-000000000001",
    })
    assert response.status_code == 200
    assert insert.call_args.args[2] == "e937025b-e50c-490c-b42b-ef7619ca4d11"


def test_missing_database_configuration_returns_service_unavailable(api, monkeypatch):
    monkeypatch.setattr(crops_repo, "get_crops", Mock(
        side_effect=crops_repo.ConfigurationError("Database is not configured"),
    ))
    response = api.post("/api/history", json={
        "crop_id": "crop-1", "planting_date": "2026-11-15", "user_id": "e937025b-e50c-490c-b42b-ef7619ca4d11",
    })
    assert response.status_code == 503


def test_failed_insert_returns_service_unavailable(api, monkeypatch, crop):
    monkeypatch.setattr(crops_repo, "get_crops", lambda: [crop])
    monkeypatch.setattr(crops_repo, "add_history", Mock(
        side_effect=crops_repo.HistoryStorageError("Unable to save planting history"),
    ))
    response = api.post("/api/history", json={
        "crop_id": "crop-1", "planting_date": "2026-11-15", "user_id": "e937025b-e50c-490c-b42b-ef7619ca4d11",
    })
    assert response.status_code == 503


def test_harvest_before_planting_is_rejected(api, monkeypatch):
    insert = Mock()
    monkeypatch.setattr(crops_repo, "add_history", insert)
    response = api.post("/api/history", json={
        "crop_id": "crop-1", "planting_date": "2026-11-15", "user_id": "e937025b-e50c-490c-b42b-ef7619ca4d11",
        "harvest_date": "2026-10-15",
    })
    assert response.status_code == 422
    insert.assert_not_called()


def test_history_insert_preserves_crop_name_and_demand_snapshot(monkeypatch, crop):
    query = Mock()
    query.insert.return_value = query
    query.execute.return_value = SimpleNamespace(data=[{"id": "history-1"}])
    database = Mock()
    database.table.return_value = query
    monkeypatch.setattr(crops_repo, "client", lambda: database)

    result = crops_repo.add_history(crop, "2026-11-15", "e937025b-e50c-490c-b42b-ef7619ca4d11", "2027-03-15")

    database.table.assert_called_once_with("planting_history")
    query.insert.assert_called_once_with({
        "crop_id": "crop-1", "planting_date": "2026-11-15", "user_id": "e937025b-e50c-490c-b42b-ef7619ca4d11",
        "plant_name": "Tomato", "soil_nutrition_demand": "H",
        "harvest_date": "2027-03-15",
    })
    assert result == [{"id": "history-1", "plant_name": "Tomato", "soil_nutrition_demand": "H"}]


def test_history_read_filters_user_and_orders_latest_planting_first(monkeypatch):
    query = Mock()
    for method in ("select", "order", "eq", "limit"):
        getattr(query, method).return_value = query
    rows = [{"id": "history-1", "plant_name": "Tomato", "soil_nutrition_demand": "H"}]
    query.execute.return_value = SimpleNamespace(data=rows)
    database = Mock()
    database.table.return_value = query
    monkeypatch.setattr(crops_repo, "client", lambda: database)

    assert crops_repo.get_history("e937025b-e50c-490c-b42b-ef7619ca4d11", limit=2) == rows

    database.table.assert_called_once_with("planting_history")
    query.order.assert_called_once_with("planting_date", desc=True)
    query.eq.assert_called_once_with("user_id", "e937025b-e50c-490c-b42b-ef7619ca4d11")
    query.limit.assert_called_once_with(2)


@pytest.mark.parametrize("code", ["PGRST204", "42703"])
def test_legacy_schema_retries_without_snapshot_columns(monkeypatch, crop, code):
    query = Mock()
    query.insert.return_value = query
    query.execute.side_effect = [
        APIError({"code": code, "message": "Missing column plant_name", "details": None, "hint": None}),
        SimpleNamespace(data=[{"id": "history-1", "crop_id": "crop-1"}]),
    ]
    database = Mock()
    database.table.return_value = query
    monkeypatch.setattr(crops_repo, "client", lambda: database)

    rows = crops_repo.add_history(crop, "2026-11-15")

    assert query.insert.call_count == 2
    assert query.insert.call_args.args[0] == {"crop_id": "crop-1", "planting_date": "2026-11-15"}
    assert rows[0]["plant_name"] == "Tomato"
    assert rows[0]["soil_nutrition_demand"] == "H"


def test_unrelated_database_error_does_not_retry_insert(monkeypatch, crop):
    query = Mock()
    query.insert.return_value = query
    query.execute.side_effect = APIError({
        "code": "42501", "message": "Permission denied", "details": None, "hint": None,
    })
    database = Mock()
    database.table.return_value = query
    monkeypatch.setattr(crops_repo, "client", lambda: database)

    with pytest.raises(crops_repo.HistoryStorageError):
        crops_repo.add_history(crop, "2026-11-15")
    query.insert.assert_called_once()


def test_missing_database_confirmation_is_not_reported_as_saved(monkeypatch, crop):
    query = Mock()
    query.insert.return_value = query
    query.execute.return_value = SimpleNamespace(data=[])
    database = Mock()
    database.table.return_value = query
    monkeypatch.setattr(crops_repo, "client", lambda: database)

    with pytest.raises(crops_repo.HistoryStorageError):
        crops_repo.add_history(crop, "2026-11-15")


def test_existing_history_snapshots_survive_crop_changes(monkeypatch):
    rows = [{"id": "history-1", "plant_name": "Old Tomato", "soil_nutrition_demand": "L"}]
    query = Mock()
    query.select.return_value = query
    query.order.return_value = query
    query.execute.return_value = SimpleNamespace(data=rows)
    database = Mock()
    database.table.return_value = query
    monkeypatch.setattr(crops_repo, "client", lambda: database)
    get_crops = Mock(side_effect=AssertionError("Stored snapshots should be retained"))
    monkeypatch.setattr(crops_repo, "get_crops", get_crops)

    assert crops_repo.get_history() == rows
    get_crops.assert_not_called()

