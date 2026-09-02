import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.models.user import User
from app.schemas.qore_versions import QoreVersionResponse
from app.services.auth.dependency import require_admin
from app.services.qore_versions.service import (
    QoreVersionError,
    QoreVersionNotFoundError,
    activate_version,
    list_versions,
    upload_version,
)

router = APIRouter()


def _to_response(row) -> QoreVersionResponse:
    return QoreVersionResponse(
        id=row.id,
        label=row.label,
        active=row.active,
        smoke_test_ok=row.smoke_test_ok,
        smoke_test_output=row.smoke_test_output,
        uploaded_by=row.uploaded_by,
        uploaded_at=row.uploaded_at,
    )


@router.get("/qore-versions", response_model=list[QoreVersionResponse])
async def list_qore_versions(admin: User = Depends(require_admin)) -> list[QoreVersionResponse]:
    return [_to_response(v) for v in list_versions()]


@router.post("/qore-versions", response_model=QoreVersionResponse)
async def upload_qore_version(
    so_file: UploadFile = File(...),
    label: str = Form(...),
    admin: User = Depends(require_admin),
) -> QoreVersionResponse:
    so_bytes = await so_file.read()
    row = upload_version(so_bytes, label, admin.username)
    logging.info(
        "admin %s uploaded QORE version %r (id=%s, smoke_test_ok=%s)",
        admin.username, label, row.id, row.smoke_test_ok,
    )
    return _to_response(row)


@router.post("/qore-versions/{version_id}/activate", response_model=QoreVersionResponse)
async def activate_qore_version(version_id: int, admin: User = Depends(require_admin)) -> QoreVersionResponse:
    try:
        row = activate_version(version_id, admin.username)
    except QoreVersionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except QoreVersionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    logging.info("admin %s activated QORE version id=%s", admin.username, version_id)
    return _to_response(row)
