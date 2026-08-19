import logging

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from app.config import settings
from app.models.user import User
from app.schemas.auth import (
    ApiTokenCreatedResponse,
    ApiTokenCreateRequest,
    ApiTokenResponse,
    LoginRequest,
    UserResponse,
)
from app.services.auth.dependency import require_user
from app.services.auth.login import authenticate
from app.services.auth.session import delete_session
from app.services.auth.tokens import create_token, list_tokens, revoke_token

router = APIRouter()


@router.post("/auth/login", response_model=UserResponse)
async def login(request: LoginRequest, response: Response) -> UserResponse:
    result = authenticate(request.username, request.password)
    if result is None:
        logging.warning("failed login attempt for username=%s", request.username)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid username or password")
    session_id, user = result
    logging.info("user %s logged in", request.username)
    response.set_cookie(
        key=settings.session_cookie_name,
        value=session_id,
        max_age=settings.session_ttl_sec,
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )
    return UserResponse(username=user.username, is_admin=user.is_admin)


@router.post("/auth/logout")
async def logout(
    response: Response,
    session_id: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> dict:
    if session_id is not None:
        delete_session(session_id)
    response.delete_cookie(settings.session_cookie_name)
    return {"logged_out": True}


@router.get("/auth/me", response_model=UserResponse)
async def me(user: User = Depends(require_user)) -> UserResponse:
    return UserResponse(username=user.username, is_admin=user.is_admin)


@router.post("/auth/tokens", response_model=ApiTokenCreatedResponse)
async def create_api_token(
    request: ApiTokenCreateRequest, user: User = Depends(require_user)
) -> ApiTokenCreatedResponse:
    token_id, raw_token, created_at, expires_at = create_token(user.id, request.name)
    logging.info("user %s created API token %r (id=%s)", user.username, request.name, token_id)
    return ApiTokenCreatedResponse(
        id=token_id, name=request.name, token=raw_token, created_at=created_at, expires_at=expires_at
    )


@router.get("/auth/tokens", response_model=list[ApiTokenResponse])
async def list_api_tokens(user: User = Depends(require_user)) -> list[ApiTokenResponse]:
    return [
        ApiTokenResponse(id=t.id, name=t.name, created_at=t.created_at, expires_at=t.expires_at)
        for t in list_tokens(user.id)
    ]


@router.delete("/auth/tokens/{token_id}")
async def delete_api_token(token_id: int, user: User = Depends(require_user)) -> dict:
    if not revoke_token(user.id, token_id):
        raise HTTPException(status_code=404, detail="token not found")
    logging.info("user %s revoked API token id=%s", user.username, token_id)
    return {"revoked": True}
