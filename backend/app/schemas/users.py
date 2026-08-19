from datetime import datetime

from pydantic import BaseModel


class UserCreateRequest(BaseModel):
    username: str


class UserCreatedResponse(BaseModel):
    """Returned once, right after creation — the raw password is never shown again."""

    id: int
    username: str
    password: str
    created_at: datetime


class UserAdminResponse(BaseModel):
    id: int
    username: str
    is_admin: bool
    created_at: datetime
