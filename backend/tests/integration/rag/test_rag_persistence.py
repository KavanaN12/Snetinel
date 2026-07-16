import pytest

from src.modules.rag.repositories.postgres_document_repository import PostgresDocumentRepository
from src.modules.rag.services.rag_service import RagService


@pytest.mark.asyncio
async def test_rag_document_persists_across_sessions(session_factory):
    async with session_factory() as write_session:
        repository = PostgresDocumentRepository(write_session)
        service = RagService(document_repository=repository)

        stored = await service.store_document(
            title="Security Playbook",
            content="This document covers security recommendations for the team.",
            source="docs",
        )

        assert stored.id is not None

    async with session_factory() as read_session:
        repository = PostgresDocumentRepository(read_session)
        service = RagService(document_repository=repository)

        results = await service.search("security", limit=5)

    assert len(results) >= 1
    assert any(result.title == "Security Playbook" for result in results)
