from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import DateTime, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.shared.db.session import Base


class ComplianceFindingModel(Base):
    __tablename__ = "compliance_findings"

    id: Mapped[str] = mapped_column(Uuid, primary_key=True, default=uuid4)
    workspace_id: Mapped[str] = mapped_column(Uuid, nullable=False, index=True)
    check_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    remediation: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    framework: Mapped[str] = mapped_column(String(50), nullable=False, default="cis-aws")
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
