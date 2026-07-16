import pytest

from src.modules.rag.services.rag_service import RagService


class StubDocumentRepository:
    def __init__(self):
        self.docs = []

    async def create_document(self, **kwargs):
        self.docs.append(kwargs)
        return kwargs

    async def list_documents(self):
        return self.docs


class StubEmbeddingProvider:
    async def embed(self, text: str) -> list[float]:
        text = text.lower()
        if "iam" in text:
            return [1.0, 0.0]
        if "pizza" in text:
            return [0.0, 1.0]
        if "auth" in text:
            return [1.0, 0.0]
        return [0.0, 1.0]


@pytest.mark.asyncio
async def test_rag_service_stores_and_searches_documents():
    service = RagService(
        document_repository=StubDocumentRepository(),
        embedding_provider=StubEmbeddingProvider(),
    )

    await service.store_document(title="Auth Guide", content="How to secure authentication flows", source="docs")
    result = await service.search("auth", limit=5)

    assert len(result) == 1
    assert result[0].title == "Auth Guide"


@pytest.mark.asyncio
async def test_rag_service_finds_documents_with_default_embedding_provider():
    service = RagService(document_repository=StubDocumentRepository())

    stored = await service.store_document(
        title="Security Playbook",
        content="This document covers security recommendations for the team.",
        source="docs",
    )
    results = await service.search("security", limit=5)

    assert len(results) == 1
    assert results[0].id == stored.id
    assert results[0].title == "Security Playbook"


@pytest.mark.asyncio
async def test_rag_service_filters_unrelated_documents_by_similarity():
    repository = StubDocumentRepository()
    repository.docs = [
        {"id": "pizza-id", "title": "Pizza Recipe", "content": "How to bake pizza", "source": "docs", "embedding": [0.0, 1.0]},
        {"id": "football-id", "title": "Football Match", "content": "A football game recap", "source": "docs", "embedding": [1.0, 0.0]},
    ]
    service = RagService(document_repository=repository, embedding_provider=StubEmbeddingProvider())

    results = await service.search("pizza", limit=5)

    assert len(results) == 1
    assert results[0].title == "Pizza Recipe"


@pytest.mark.asyncio
async def test_rag_service_returns_iam_related_documents_only():
    repository = StubDocumentRepository()
    repository.docs = [
        {"id": "iam-id", "title": "IAM Access Management", "content": "How to manage IAM roles", "source": "docs", "embedding": [1.0, 0.0]},
        {"id": "football-id", "title": "Football Match", "content": "A football game recap", "source": "docs", "embedding": [0.0, 1.0]},
    ]
    service = RagService(document_repository=repository, embedding_provider=StubEmbeddingProvider())

    results = await service.search("iam", limit=5)

    assert len(results) == 1
    assert results[0].title == "IAM Access Management"
