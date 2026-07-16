from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


@dataclass(slots=True)
class KnowledgeDocument:
    id: UUID | None = None
    title: str = ""
    content: str = ""
    source: str = ""
    embedding: list[float] = field(default_factory=list)
    created_at: datetime | None = None
