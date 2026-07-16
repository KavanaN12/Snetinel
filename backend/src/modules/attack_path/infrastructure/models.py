from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.session import Base


class AttackPathModel(Base):
    __tablename__ = "attack_paths"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[str] = mapped_column(Uuid, nullable=False, index=True)
    attack_type: Mapped[str] = mapped_column(String(100), nullable=False)
    steps: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True, default=list)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
