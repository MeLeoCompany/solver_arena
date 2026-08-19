import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.database import SessionLocal
from app.models.user import ApiToken, User


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_token(user_id: int, name: str) -> tuple[int, str, datetime, datetime]:
    """Returns (token_id, raw_token, created_at, expires_at). raw_token is
    shown to the caller once — only its hash is stored.
    """
    raw_token = secrets.token_urlsafe(32)
    created_at = datetime.now(timezone.utc).replace(tzinfo=None)
    expires_at = created_at + timedelta(seconds=settings.api_token_ttl_sec)

    with SessionLocal() as db:
        token = ApiToken(
            user_id=user_id,
            name=name,
            token_hash=_hash_token(raw_token),
            created_at=created_at,
            expires_at=expires_at,
        )
        db.add(token)
        db.commit()
        token_id = token.id

    return token_id, raw_token, created_at, expires_at


def list_tokens(user_id: int) -> list[ApiToken]:
    with SessionLocal() as db:
        return (
            db.query(ApiToken)
            .filter_by(user_id=user_id)
            .order_by(ApiToken.created_at.desc())
            .all()
        )


def revoke_token(user_id: int, token_id: int) -> bool:
    with SessionLocal() as db:
        token = db.get(ApiToken, token_id)
        if token is None or token.user_id != user_id:
            return False
        db.delete(token)
        db.commit()
        return True


def get_user_for_token(raw_token: str) -> User | None:
    with SessionLocal() as db:
        token = db.query(ApiToken).filter_by(token_hash=_hash_token(raw_token)).first()
        if token is None:
            return None
        if token.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
            db.delete(token)
            db.commit()
            return None
        return db.get(User, token.user_id)
