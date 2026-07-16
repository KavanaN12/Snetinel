from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class AttackPathRepository(ABC):
    @abstractmethod
    async def delete_for_workspace(self, workspace_id: UUID) -> None:
        raise NotImplementedError

    @abstractmethod
    async def create(self, *, workspace_id: UUID, attack_type: str, steps: list[dict], details: dict):
        raise NotImplementedError

    @abstractmethod
    async def list_for_workspace(self, workspace_id: UUID):
        raise NotImplementedError
