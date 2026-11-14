from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Terawise API", version="1.0.0")


class HealthResponse(BaseModel):
    status: str
    message: str


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", message="Terawise API is running")
