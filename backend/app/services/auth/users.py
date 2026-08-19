import secrets
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models.user import User
from app.services.auth.password import hash_password


def create_user(username: str) -> tuple[User, str]:
    """Returns (user, raw_password). raw_password is shown to the caller
    once — only its hash is stored, same convention as create_token.
    New users are always non-admin — granting admin rights isn't exposed
    through the app, only via direct DB access.
    """
    raw_password = secrets.token_urlsafe(12)
    with SessionLocal() as db:
        user = User(
            username=username,
            password_hash=hash_password(raw_password),
            is_admin=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user, raw_password


def list_users() -> list[User]:
    with SessionLocal() as db:
        return db.query(User).order_by(User.created_at.desc()).all()


def delete_user(user_id: int) -> bool:
    with SessionLocal() as db:
        user = db.get(User, user_id)
        if user is None:
            return False
        db.delete(user)
        db.commit()
        return True
