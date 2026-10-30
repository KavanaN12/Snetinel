from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.session import Base


class IamAgentRunModel(Base):
    __tablename__ = "iam_agent_runs"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[str] = mapped_column(
        Uuid,
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    lifecycle: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    attempts: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    baseline_path_count: Mapped[int] = mapped_column(Integer, nullable=False)
    final_path_count: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluation: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
