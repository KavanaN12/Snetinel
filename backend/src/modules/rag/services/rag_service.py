from __future__ import annotations

import hashlib
import math
import re

from src.modules.rag.domain.entities import KnowledgeDocument
from src.modules.rag.repositories.document_repository import DocumentRepository


class EmbeddingProvider:
    async def embed(self, text: str) -> list[float]:
        if not text:
            return []

        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if not tokens:
            return []

        vector = [0.0] * 32
        for token in tokens:
            index = int(hashlib.blake2b(token.encode("utf-8"), digest_size=8).hexdigest(), 16) % len(vector)
            vector[index] += 1.0
        return vector


class RagService:
    MIN_SIMILARITY_THRESHOLD = 0.1

    def __init__(self, document_repository: DocumentRepository, embedding_provider: EmbeddingProvider | None = None) -> None:
        self._document_repository = document_repository
        self._embedding_provider = embedding_provider or EmbeddingProvider()

    async def store_document(self, *, title: str, content: str, source: str) -> KnowledgeDocument:
        embedding = await self._embedding_provider.embed(content)
        result = await self._document_repository.create_document(title=title, content=content, source=source, embedding=embedding)
        return self._coerce_document(result)

    async def search(self, query: str, *, limit: int = 5) -> list[KnowledgeDocument]:
        if limit <= 0:
            return []

        documents = await self._document_repository.list_documents()
        query_embedding = await self._embedding_provider.embed(query)
        if not query_embedding:
            return []

        scored = []
        for document in documents:
            normalized = self._coerce_document(document)
            if not normalized.embedding:
                continue

            similarity = self._cosine_similarity(query_embedding, normalized.embedding)
            if similarity < self.MIN_SIMILARITY_THRESHOLD:
                continue

            scored.append((similarity, normalized))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [document for _, document in scored[:limit]]

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0

        if len(left) != len(right):
            length = min(len(left), len(right))
            left = left[:length]
            right = right[:length]

        dot_product = sum(float(l) * float(r) for l, r in zip(left, right, strict=False))
        left_norm = math.sqrt(sum(float(value) * float(value) for value in left))
        right_norm = math.sqrt(sum(float(value) * float(value) for value in right))

        if not left_norm or not right_norm:
            return 0.0

        return dot_product / (left_norm * right_norm)

    def _coerce_document(self, document: object) -> KnowledgeDocument:
        if isinstance(document, KnowledgeDocument):
            return document
        if isinstance(document, dict):
            return KnowledgeDocument(
                id=document.get("id"),
                title=document.get("title", ""),
                content=document.get("content", ""),
                source=document.get("source", ""),
                embedding=document.get("embedding") or [],
                created_at=document.get("created_at"),
            )
        return KnowledgeDocument(
            id=getattr(document, "id", None),
            title=getattr(document, "title", ""),
            content=getattr(document, "content", ""),
            source=getattr(document, "source", ""),
            embedding=getattr(document, "embedding", []) or [],
            created_at=getattr(document, "created_at", None),
        )
