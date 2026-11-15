from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from httpx import HTTPError
from postgrest.exceptions import APIError

from app.services import crops_repo
from app.services.agronomy import recommend
from app.services.crops_repo import ConfigurationError, HistoryStorageError
from app.services.history_auth import get_history_user

router = APIRouter(prefix="/api", tags=["recommendation"])


class RecommendationRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    farm_area_m2: float = Field(gt=0, description="Farm area in square metres")
    tank_water_l: float = Field(ge=0, description="Water available in the tank, in litres")
    planting_date: date


class PlantingRecord(BaseModel):
    crop_id: str = Field(min_length=1)
    planting_date: date
    harvest_date: date | None = None

    @model_validator(mode="after")
    def validate_dates(self):
        if self.harvest_date and self.harvest_date < self.planting_date:
            raise ValueError("Harvest date must be on or after planting date")
        return self


@router.get("/crops")
def list_crops():
    """Crop list for the UI, using the same identifiers as the recommendation engine."""
    try:
        crops = crops_repo.get_crops()
    except ConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error))
    return [
        {
            "id": crop["id"],
            "name": crop["name"],
            "demand": crop.get("soil_nutrient_demand"),
            "growth_duration_months": crop.get("growth_duration_months"),
        }
        for crop in crops
    ]


@router.post("/recommend")
def post_recommend(request: RecommendationRequest, user_id: str = Depends(get_history_user)):
    try:
        return recommend(
            request.lat,
            request.lon,
            request.farm_area_m2,
            request.tank_water_l,
            request.planting_date,
            user_id,
        )
    except ConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error))


@router.get("/history")
def list_history(user_id: str = Depends(get_history_user)):
    try:
        return crops_repo.get_history(user_id)
    except ConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except HistoryStorageError as error:
        raise HTTPException(status_code=503, detail=str(error))


@router.post("/history")
def create_history(record: PlantingRecord, user_id: str = Depends(get_history_user)):
    try:
        crops = {str(crop["id"]): crop for crop in crops_repo.get_crops()}
    except ConfigurationError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except (APIError, HTTPError) as error:
        raise HTTPException(status_code=503, detail="Unable to load crops. Please try again.") from error

    crop = crops.get(record.crop_id)
    if crop is None:
        raise HTTPException(status_code=404, detail="Unknown crop")

    try:
        return crops_repo.add_history(
            crop,
            record.planting_date.isoformat(),
            user_id,
            record.harvest_date.isoformat() if record.harvest_date else None,
        )
    except (ConfigurationError, HistoryStorageError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
