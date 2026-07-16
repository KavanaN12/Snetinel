from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.session import Base


class DriftEventModel(Base):
    __tablename__ = "drift_events"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[str] = mapped_column(Uuid, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(255), nullable=False)
    previous_value: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    current_value: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
