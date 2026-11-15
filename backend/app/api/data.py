from fastapi import APIRouter, HTTPException

from app.services.data_loader import DATA_FILES, load_all, load_dataset

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("")
async def get_all_data():
    try:
        return load_all()
    except FileNotFoundError as error:
        raise HTTPException(status_code=404, detail=f"Data file missing: {error.filename}")
    except ValueError:
        raise HTTPException(status_code=500, detail="A data file contains invalid JSON")


@router.get("/{name}")
async def get_dataset(name: str):
    if name not in DATA_FILES:
        raise HTTPException(status_code=404, detail="Unknown dataset")
    try:
        return load_dataset(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Data file missing")
    except ValueError:
        raise HTTPException(status_code=500, detail="Data file contains invalid JSON")