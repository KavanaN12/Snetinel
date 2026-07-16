from __future__ import annotations

from fastapi import APIRouter, Depends

from src.modules.rag.repositories.postgres_document_repository import PostgresDocumentRepository
from src.modules.rag.services.rag_service import RagService
from src.shared.db.session import get_db_session
from src.shared.security.dependencies import get_current_user_id

router = APIRouter(prefix="/rag", tags=["rag"])


def get_rag_service(session=Depends(get_db_session)) -> RagService:
    return RagService(document_repository=PostgresDocumentRepository(session))


@router.post("/documents")
async def store_document(
    title: str,
    content: str,
    source: str,
    current_user_id: str = Depends(get_current_user_id),
    service: RagService = Depends(get_rag_service),
) -> dict[str, object]:
    del current_user_id
    document = await service.store_document(title=title, content=content, source=source)
    return {"id": str(document.id), "title": document.title, "source": document.source}


@router.get("/search")
async def search_documents(
    query: str,
    current_user_id: str = Depends(get_current_user_id),
    service: RagService = Depends(get_rag_service),
) -> list[dict[str, object]]:
    del current_user_id
    documents = await service.search(query, limit=5)
    return [{"id": str(document.id), "title": document.title, "source": document.source} for document in documents]
