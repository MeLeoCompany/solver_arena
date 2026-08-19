from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import JobState
from app.schemas.jobs import JobResponse


class BatchFlagsRequest(BaseModel):
    flags: dict[str, Any] = Field(default_factory=dict)


class BatchResponse(BaseModel):
    batch_id: str
    solver: str
    state: JobState
    total: int
    completed: int
    created_by: str | None = None
    created_at: datetime
    jobs: list[JobResponse] = []


class BatchCancelResponse(BaseModel):
    batch_id: str
    cancelling: bool
