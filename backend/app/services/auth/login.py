from app.database import SessionLocal
from app.models.user import User
from app.services.auth.password import verify_password
from app.services.auth.session import create_session


def authenticate(username: str, password: str) -> tuple[str, User] | None:
    """Returns (session_id, user) if credentials are valid, else None."""
    with SessionLocal() as db:
        user = db.query(User).filter_by(username=username).first()
        if user is None or not verify_password(password, user.password_hash):
            return None
        db.expunge(user)
    return create_session(user.id), user
