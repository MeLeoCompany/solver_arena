from datetime import datetime, timezone

from app.config import settings
from app.database import SessionLocal
from app.models.user import User
from app.services.auth.password import hash_password


def seed_admin_user() -> None:
    if not settings.admin_username or not settings.admin_password:
        return
    with SessionLocal() as db:
        existing = db.query(User).filter_by(username=settings.admin_username).first()
        if existing is not None:
            if not existing.is_admin:
                existing.is_admin = True
                db.commit()
            return
        db.add(
            User(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
                is_admin=True,
                created_at=datetime.now(timezone.utc),
            )
        )
        db.commit()
