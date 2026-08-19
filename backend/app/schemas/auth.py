from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    username: str
    is_admin: bool


class ApiTokenCreateRequest(BaseModel):
    name: str


class ApiTokenCreatedResponse(BaseModel):
    """Returned once, right after creation — the raw token is never shown again."""

    id: int
    name: str
    token: str
    created_at: datetime
    expires_at: datetime


class ApiTokenResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    expires_at: datetime
