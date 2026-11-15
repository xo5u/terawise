"""Reads of the crop/fertilizer/history tables in Supabase."""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from httpx import HTTPError
from postgrest.exceptions import APIError
from supabase import create_client

from app.services.crop_defaults import WEIGHTS, apply_defaults

REPO_ROOT = Path(__file__).resolve().parents[3]

WEIGHT_TOTAL_TOLERANCE = 1e-6


class ConfigurationError(RuntimeError):
    """Raised when the database is missing configuration the rules depend on."""


class HistoryStorageError(RuntimeError):
    """Raised when planting history cannot be read or persisted."""


@lru_cache(maxsize=1)
def client():
    load_dotenv(REPO_ROOT / ".env")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        raise ConfigurationError("SUPABASE_URL and a Supabase key must be set in .env")
    return create_client(url, key)


def get_crops():
    rows = client().table("crops").select("*").order("name").execute().data
    return [apply_defaults(crop) for crop in rows]


def get_fertilizers():
    return client().table("fertilizers").select("*").execute().data


def get_weights():
    """The fixed factor weights, applied to every eligible crop."""
    total = sum(WEIGHTS.values())
    if abs(total - 1.0) > WEIGHT_TOTAL_TOLERANCE:
        raise ConfigurationError(f"Scoring weights must total 1, found {total:.4f}")
    return dict(WEIGHTS)


def get_history(user_id=None, limit=None):
    query = client().table("planting_history").select("*").order("planting_date", desc=True)
    if user_id:
        query = query.eq("user_id", user_id)
    if limit:
        query = query.limit(limit)
    try:
        rows = query.execute().data
        if any(row.get("plant_name") is None or row.get("soil_nutrition_demand") is None for row in rows):
            crops = {str(crop["id"]): crop for crop in get_crops()}
            return [_history_display(row, crops.get(str(row.get("crop_id")))) for row in rows]
        return rows
    except (APIError, HTTPError) as error:
        raise HistoryStorageError("Unable to load planting history. Please try again.") from error


def _history_display(row, crop):
    """Supply display values for legacy tables; migrated rows keep their snapshots."""
    row = dict(row)
    if crop:
        if row.get("plant_name") is None:
            row["plant_name"] = crop["name"]
        if row.get("soil_nutrition_demand") is None:
            row["soil_nutrition_demand"] = crop.get("soil_nutrient_demand")
    return row


def _missing_snapshot_columns(error):
    return str(error.code) in {"PGRST204", "42703"} and any(
        name in str(error) for name in ("plant_name", "soil_nutrition_demand")
    )


def add_history(crop, planting_date, user_id=None, harvest_date=None):
    """Record a planting, including immutable crop snapshots when supported."""
    record = {
        "crop_id": crop["id"],
        "planting_date": planting_date,
        "plant_name": crop["name"],
        "soil_nutrition_demand": crop.get("soil_nutrient_demand"),
    }
    if user_id:
        record["user_id"] = user_id
    if harvest_date:
        record["harvest_date"] = harvest_date
    try:
        try:
            rows = client().table("planting_history").insert(record).execute().data
        except APIError as error:
            if not _missing_snapshot_columns(error):
                raise
            # Legacy deployments predate migration 001. Persist the planting in
            # their existing table; the migration enables immutable snapshots.
            base_record = {
                key: value for key, value in record.items()
                if key not in {"plant_name", "soil_nutrition_demand"}
            }
            rows = client().table("planting_history").insert(base_record).execute().data
    except (APIError, HTTPError) as error:
        raise HistoryStorageError("Unable to save planting history. Please try again.") from error
    if not rows:
        raise HistoryStorageError("The database did not confirm the planting was saved.")
    return [_history_display(row, crop) for row in rows]
