"""Guest authentication for planting history without account registration."""

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

from app.services.history_auth import create_guest_session, refresh_guest_session

router = APIRouter(prefix="/api", tags=["session"])


class RefreshSessionRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=8192)


@router.post("/session")
def create_session(response: Response):
    response.headers["Cache-Control"] = "no-store"
    return create_guest_session()


@router.post("/session/refresh")
def refresh_session(request: RefreshSessionRequest, response: Response):
    response.headers["Cache-Control"] = "no-store"
    return refresh_guest_session(request.refresh_token)
