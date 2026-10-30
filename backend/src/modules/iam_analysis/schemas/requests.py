from pydantic import BaseModel, Field


class IamAgentRunRequest(BaseModel):
    max_attempts: int = Field(default=5, ge=1, le=5)
