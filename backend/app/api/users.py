import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError

from app.models.user import User
from app.schemas.users import UserAdminResponse, UserCreatedResponse, UserCreateRequest
from app.services.auth.dependency import require_admin
from app.services.auth.users import create_user, delete_user, list_users

router = APIRouter()


@router.post("/users", response_model=UserCreatedResponse)
async def create_user_endpoint(
    request: UserCreateRequest, admin: User = Depends(require_admin)
) -> UserCreatedResponse:
    try:
        user, raw_password = create_user(request.username)
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail="username already taken") from exc
    logging.info("admin %s created user %r (id=%s)", admin.username, user.username, user.id)
    return UserCreatedResponse(
        id=user.id, username=user.username, password=raw_password, created_at=user.created_at
    )


@router.get("/users", response_model=list[UserAdminResponse])
async def list_users_endpoint(admin: User = Depends(require_admin)) -> list[UserAdminResponse]:
    return [
        UserAdminResponse(id=u.id, username=u.username, is_admin=u.is_admin, created_at=u.created_at)
        for u in list_users()
    ]


@router.delete("/users/{user_id}")
async def delete_user_endpoint(user_id: int, admin: User = Depends(require_admin)) -> dict:
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="cannot delete your own account")
    if not delete_user(user_id):
        raise HTTPException(status_code=404, detail="user not found")
    logging.info("admin %s deleted user id=%s", admin.username, user_id)
    return {"deleted": True}
