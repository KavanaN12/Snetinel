from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AIExplanationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    summary: str
    details: list[str]
    confidence: str
    fallback_used: bool
