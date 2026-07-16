"""
Response schemas — map domain entities/value objects to the API's public
shape. Domain entities (User, TokenPair) never get returned directly from a
controller; they always pass through one of these.
"""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UserResponse(BaseModel):
    id: UUID
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
