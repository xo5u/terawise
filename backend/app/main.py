
import httpx

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.services.geocoding import get_region_name


app = FastAPI(
    title="Terawise API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


class Location(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class LocationResponse(BaseModel):
    lat: float
    lng: float
    region: str
    country: str | None = None
    display_name: str | None = None


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "message": "Terawise API is running"
    }


@app.post("/api/location", response_model=LocationResponse)
async def set_location(location: Location):

    try:
        result = await get_region_name(
            location.lat,
            location.lng
        )

        if result is None:
            raise HTTPException(
                status_code=404,
                detail="Could not identify this region"
            )

        return result

    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Location service is unavailable"
        )
