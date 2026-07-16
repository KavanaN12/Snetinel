from __future__ import annotations

from typing import Protocol


class AIProvider(Protocol):
    async def generate_text(self, prompt: str, *, system_prompt: str | None = None) -> str: ...
