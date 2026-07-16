"""SQLAlchemy ORM models for discovery runs."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.session import Base


class DiscoveryRunModel(Base):
    __tablename__ = "discovery_runs"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    resource_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    discovered_resources: Mapped[list[dict[str, str]]] = mapped_column(JSON, nullable=False, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
