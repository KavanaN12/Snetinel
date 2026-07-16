from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class DashboardSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    severity_counts: dict[str, int]
    finding_counts: dict[str, int]
    resource_counts: dict[str, int]
    attack_path_counts: dict[str, int]
