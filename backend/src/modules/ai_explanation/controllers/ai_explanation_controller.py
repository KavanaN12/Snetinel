from __future__ import annotations

from fastapi import APIRouter, Depends

from src.modules.ai_explanation.schemas.requests import AIExplanationRequest
from src.modules.ai_explanation.schemas.responses import AIExplanationResponse
from src.modules.ai_explanation.services.ai_explanation_service import AIExplanationService
from src.shared.security.dependencies import get_current_user_id

router = APIRouter(prefix="/ai-explanation", tags=["ai-explanation"])


def get_ai_explanation_service() -> AIExplanationService:
    return AIExplanationService()


@router.post("/explain", response_model=AIExplanationResponse)
async def explain_finding(
    payload: AIExplanationRequest,
    current_user_id: str = Depends(get_current_user_id),
    service: AIExplanationService = Depends(get_ai_explanation_service),
) -> AIExplanationResponse:
    del current_user_id
    result = await service.explain_finding(payload.model_dump())
    return result
