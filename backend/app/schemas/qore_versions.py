from datetime import datetime

from pydantic import BaseModel


class QoreVersionResponse(BaseModel):
    id: int
    label: str
    active: bool
    smoke_test_ok: bool
    smoke_test_output: str | None
    uploaded_by: str | None
    uploaded_at: datetime
