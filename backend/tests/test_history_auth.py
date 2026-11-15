from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from supabase_auth.errors import AuthApiError

from app.api.session import router
from app.services import history_auth

USER_ID = "e937025b-e50c-490c-b42b-ef7619ca4d11"


@pytest.fixture
def api(monkeypatch):
    client = Mock()
    monkeypatch.setattr(history_auth, "auth_client", lambda: client)
    app = FastAPI()
    app.include_router(router)

    @app.get("/owned")
    def owned(user_id=Depends(history_auth.get_history_user)):
        return {"user_id": user_id}

    return TestClient(app), client


def auth_response():
    return SimpleNamespace(user=SimpleNamespace(id=USER_ID), session=SimpleNamespace(
        access_token="access", refresh_token="refresh", expires_at=1800000000,
    ))


def test_guest_session_uses_auth_user_and_prevents_caching(api):
    http, client = api
    client.auth.sign_in_anonymously.return_value = auth_response()
    response = http.post("/api/session")
    assert response.status_code == 200
    assert response.json()["user_id"] == USER_ID
    assert response.json()["access_token"] == "access"
    assert response.headers["cache-control"] == "no-store"
    client.auth.sign_in_anonymously.assert_called_once_with()


def test_disabled_anonymous_signup_has_actionable_error(api):
    http, client = api
    client.auth.sign_in_anonymously.side_effect = AuthApiError(
        "Anonymous sign-ins are disabled", 422, "anonymous_provider_disabled",
    )
    response = http.post("/api/session")
    assert response.status_code == 503
    assert "Enable anonymous sign-ins" in response.json()["detail"]


def test_refresh_uses_provided_token(api):
    http, client = api
    client.auth.refresh_session.return_value = auth_response()
    response = http.post("/api/session/refresh", json={"refresh_token": "old-refresh"})
    assert response.status_code == 200
    client.auth.refresh_session.assert_called_once_with("old-refresh")


def test_invalid_refresh_is_unauthorized(api):
    http, client = api
    client.auth.refresh_session.side_effect = AuthApiError("Invalid refresh token", 400, None)
    assert http.post("/api/session/refresh", json={"refresh_token": "bad"}).status_code == 401


def test_history_requires_bearer_session(api):
    http, client = api
    assert http.get("/owned").status_code == 401
    client.auth.get_user.assert_not_called()


def test_history_owner_comes_from_validated_token(api):
    http, client = api
    client.auth.get_user.return_value = SimpleNamespace(user=SimpleNamespace(id=USER_ID))
    response = http.get("/owned", headers={"Authorization": "Bearer verified-access"})
    assert response.json() == {"user_id": USER_ID}
    client.auth.get_user.assert_called_once_with("verified-access")


def test_invalid_history_token_is_rejected(api):
    http, client = api
    client.auth.get_user.side_effect = AuthApiError("Invalid JWT", 401, None)
    assert http.get("/owned", headers={"Authorization": "Bearer bad"}).status_code == 401
