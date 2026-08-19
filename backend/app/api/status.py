from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.services.status.stream import stream_status

router = APIRouter()


@router.get("/system/status/stream")
async def stream_system_status() -> StreamingResponse:
    return StreamingResponse(stream_status(), media_type="text/event-stream")
