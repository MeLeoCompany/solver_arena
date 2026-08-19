import secrets
from datetime import datetime, timedelta, timezone

from app.config import settings
from app.database import SessionLocal
from app.models.user import Session as SessionModel
from app.models.user import User


def _utcnow_naive() -> datetime:
    # SQLite drops tzinfo on round-trip, so datetimes compared against
    # values read back from the DB must be naive UTC on both sides.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def create_session(user_id: int) -> str:
    session_id = secrets.token_urlsafe(32)
    now = _utcnow_naive()
    with SessionLocal() as db:
        db.add(
            SessionModel(
                id=session_id,
                user_id=user_id,
                created_at=now,
                expires_at=now + timedelta(seconds=settings.session_ttl_sec),
            )
        )
        db.commit()
    return session_id


def get_user_for_session(session_id: str) -> User | None:
    with SessionLocal() as db:
        record = db.get(SessionModel, session_id)
        if record is None:
            return None
        if record.expires_at < _utcnow_naive():
            db.delete(record)
            db.commit()
            return None
        return db.get(User, record.user_id)


def delete_session(session_id: str) -> None:
    with SessionLocal() as db:
        record = db.get(SessionModel, session_id)
        if record is not None:
            db.delete(record)
            db.commit()
