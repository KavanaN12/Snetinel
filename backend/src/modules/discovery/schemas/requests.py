"""Discovery request schemas."""

from pydantic import BaseModel, Field


class DiscoveryRunRequest(BaseModel):
    """Request payload for triggering discovery."""

    source: str = Field(default="manual", description="Origin of the discovery trigger")
