from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from app.services.chat import ChatConfigError, ChatUpstreamError, generate_reply

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class FarmContext(BaseModel):
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    acres: float | None = Field(default=None, ge=0)
    hectares: float | None = Field(default=None, ge=0)
    last_crop: str | None = Field(default=None, max_length=100)
    water_source: str | None = Field(default=None, max_length=100)
    budget: str | None = Field(default=None, max_length=100)
    analysis: dict | None = None


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
    farm: FarmContext | None = None

    @model_validator(mode="after")
    def last_message_from_user(self):
        if self.messages[-1].role != "user":
            raise ValueError("The last message must come from the user")
        return self


class Source(BaseModel):
    title: str
    url: str


class ChatResponse(BaseModel):
    reply: str
    sources: list[Source] = []


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        return await generate_reply(
            [m.model_dump() for m in request.messages],
            request.farm.model_dump() if request.farm else None,
        )
    except ChatConfigError as error:
        raise HTTPException(status_code=503, detail=str(error))
    except ChatUpstreamError as error:
        raise HTTPException(status_code=502, detail=str(error))