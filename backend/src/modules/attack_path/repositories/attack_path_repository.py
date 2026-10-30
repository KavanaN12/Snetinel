from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class AttackPathRepository(ABC):
    @abstractmethod
    async def delete_for_workspace(self, workspace_id: UUID | str) -> None:
        ...

    @abstractmethod
    async def create(
        self,
        *,
        workspace_id: UUID | str,
        attack_type: str,
        steps: list[dict],
        details: dict,
    ):
        ...

    @abstractmethod
    async def list_for_workspace(self, workspace_id: UUID | str):
        ...
