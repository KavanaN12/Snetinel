from __future__ import annotations

from src.modules.ai_explanation.providers.base import AIProvider
from src.modules.ai_explanation.providers.gemini_provider import GeminiProvider


class ProductionAIExplanationService:
    def __init__(self, provider: AIProvider | None = None) -> None:
        self._provider = provider or GeminiProvider()

    async def explain_finding(self, finding: str) -> str:
        prompt = f"Explain the security finding in clear business language and include a mitigation suggestion.\n\nFinding: {finding}"
        return await self._provider.generate_text(prompt, system_prompt="You are a concise security analyst.")

    async def explain_attack_path(self, attack_path: str) -> str:
        prompt = f"Summarize the attack path and the likely impact to the organization.\n\nAttack path: {attack_path}"
        return await self._provider.generate_text(prompt, system_prompt="You are a concise security analyst.")
