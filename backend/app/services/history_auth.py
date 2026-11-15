"""Supabase guest sessions and verified planting-history ownership."""

import os
from uuid import UUID

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from httpx import HTTPError
from supabase import create_client
from supabase_auth.errors import AuthError

from app.services.crops_repo import REPO_ROOT

bearer = HTTPBearer(auto_error=False)


def auth_client():
    """Session changes must never mutate the cached service/database client."""
    load_dotenv(REPO_ROOT / ".env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_SECRET_KEY")
    if not url or not key:
        raise HTTPException(503, "Supabase authentication is not configured.")
    return create_client(url, key)


def session_payload(response):
    session, user = response.session, response.user
    if not session or not user:
        raise HTTPException(503, "Authentication did not return a guest session. Please try again.")
    return {
        "user_id": str(UUID(str(user.id))),
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
        "expires_at": session.expires_at,
    }


def create_guest_session():
    try:
        return session_payload(auth_client().auth.sign_in_anonymously())
    except AuthError as error:
        if "anonymous" in str(error).lower() and "disabled" in str(error).lower():
            raise HTTPException(503, "Enable anonymous sign-ins in Supabase Authentication settings to save planting history.") from error
        raise HTTPException(503, "Unable to create a guest session. Please try again.") from error
    except HTTPError as error:
        raise HTTPException(503, "Authentication service is unavailable. Please try again.") from error


def refresh_guest_session(refresh_token):
    try:
        return session_payload(auth_client().auth.refresh_session(refresh_token))
    except AuthError as error:
        raise HTTPException(401, "Guest session expired. Please start a new session.") from error
    except HTTPError as error:
        raise HTTPException(503, "Authentication service is unavailable. Please try again.") from error


def get_history_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None:
        raise HTTPException(401, "A guest session is required.", headers={"WWW-Authenticate": "Bearer"})
    try:
        response = auth_client().auth.get_user(credentials.credentials)
        if response is None or response.user is None:
            raise HTTPException(401, "Invalid guest session.")
        return str(UUID(str(response.user.id)))
    except (AuthError, ValueError) as error:
        raise HTTPException(401, "Invalid or expired guest session.", headers={"WWW-Authenticate": "Bearer"}) from error
    except HTTPError as error:
        raise HTTPException(503, "Authentication service is unavailable. Please try again.") from error
