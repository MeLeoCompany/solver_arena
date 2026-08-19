from datetime import datetime

from pydantic import BaseModel


class SolverResponse(BaseModel):
    key: str
    label: str
    parameters: list[str]
    available: bool
    availability_detail: str | None = None
    availability_checked_at: datetime | None = None
