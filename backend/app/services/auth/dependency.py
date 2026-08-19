from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings
from app.models.user import User
from app.services.auth.session import get_user_for_session
from app.services.auth.tokens import get_user_for_token

_bearer_auth = HTTPBearer(auto_error=False)


def require_user(
    session_id: str | None = Cookie(default=None, alias=settings.session_cookie_name),
    bearer: HTTPAuthorizationCredentials | None = Depends(_bearer_auth),
) -> User:
    if bearer is not None:
        user = get_user_for_token(bearer.credentials)
        if user is not None:
            return user

    if session_id is not None:
        user = get_user_for_session(session_id)
        if user is not None:
            return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")


def require_admin(user: User = Depends(require_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin access required")
    return user
