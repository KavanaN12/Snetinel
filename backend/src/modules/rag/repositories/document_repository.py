from __future__ import annotations

from typing import Protocol

from src.modules.rag.domain.entities import KnowledgeDocument


class DocumentRepository(Protocol):
    async def create_document(self, *, title: str, content: str, source: str, embedding: list[float] | None = None) -> KnowledgeDocument: ...

    async def list_documents(self) -> list[KnowledgeDocument]: ...
