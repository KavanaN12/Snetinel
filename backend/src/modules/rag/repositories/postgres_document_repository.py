from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.rag.domain.entities import KnowledgeDocument
from src.modules.rag.infrastructure.models import KnowledgeDocumentModel


class PostgresDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_document(self, *, title: str, content: str, source: str, embedding: list[float] | None = None) -> KnowledgeDocument:
        model = KnowledgeDocumentModel(title=title, content=content, source=source, embedding=embedding or [])
        self._session.add(model)
        await self._session.flush()
        await self._session.commit()
        return KnowledgeDocument(id=model.id, title=model.title, content=model.content, source=model.source, embedding=model.embedding or [], created_at=model.created_at)

    async def list_documents(self) -> list[KnowledgeDocument]:
        result = await self._session.execute(select(KnowledgeDocumentModel))
        models = result.scalars().all()
        return [KnowledgeDocument(id=model.id, title=model.title, content=model.content, source=model.source, embedding=model.embedding or [], created_at=model.created_at) for model in models]
