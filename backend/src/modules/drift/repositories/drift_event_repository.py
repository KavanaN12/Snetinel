from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.modules.drift.domain.entities import DriftEvent


class DriftEventRepository(Protocol):
    async def create_event(self, *, workspace_id: UUID | str, event_type: str, resource_type: str, resource_id: str, previous_value: dict | None, current_value: dict | None) -> DriftEvent: ...

    async def list_for_workspace(self, workspace_id: UUID | str) -> list[DriftEvent]: ...
