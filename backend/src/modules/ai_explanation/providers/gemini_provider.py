from __future__ import annotations

import os

from google import generativeai as genai

from src.modules.ai_explanation.providers.base import AIProvider


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str | None = None) -> None:
        self._api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        if self._api_key:
            genai.configure(api_key=self._api_key)

    async def generate_text(self, prompt: str, *, system_prompt: str | None = None) -> str:
        if not self._api_key:
            return "Gemini provider is not configured."
        model = genai.GenerativeModel("gemini-1.5-flash")
        full_prompt = prompt if system_prompt is None else f"{system_prompt}\n\n{prompt}"
        response = model.generate_content(full_prompt)
        return getattr(response, "text", str(response))
