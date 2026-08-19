from typing import Any

from pydantic import BaseModel, Field


class CplexSolveRequest(BaseModel):
    flags: dict[str, Any] = Field(default_factory=dict)
    job_id: str | None = None
