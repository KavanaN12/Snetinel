from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.session import Base


class ScenarioRunModel(Base):
    __tablename__ = "scenario_runs"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[str] = mapped_column(
        Uuid,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scenario_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    resource_manifest: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    expected_results: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    actual_results: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
