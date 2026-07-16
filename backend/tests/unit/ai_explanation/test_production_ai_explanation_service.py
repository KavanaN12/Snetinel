import pytest

from src.modules.ai_explanation.services.ai_explanation_service import AIExplanationService


class StubProvider:
    async def generate_text(self, prompt: str, *, system_prompt: str | None = None) -> str:
        return "provider summary"


@pytest.mark.asyncio
async def test_ai_explanation_service_uses_provider_when_available():
    service = AIExplanationService(provider=StubProvider())
    finding = {
        "title": "Public EC2",
        "severity": "high",
        "evidence_subgraph": {"attack_type": "ec2_public"},
        "affected_resource_ids": ["i-123"],
    }

    result = await service.explain_finding(finding)

    assert result.summary == "provider summary"
    assert result.confidence == "high"
    assert result.fallback_used is False
