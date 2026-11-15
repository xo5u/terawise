from fastapi import APIRouter, Query

from app.services.analysis import analyze

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("")
def get_analysis(
    lat: float = Query(ge=-90, le=90),
    lon: float = Query(ge=-180, le=180),
    months: int = Query(default=12, ge=1, le=24),
):
    # Defined with `def` so FastAPI runs the blocking source requests in a
    # threadpool instead of stalling the event loop.
    return analyze(lat, lon, months)
