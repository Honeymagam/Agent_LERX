from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session
from .config import get_settings
from .database import get_db
from .models import User

password_hash = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)


def ensure_initial_admin(db: Session) -> None:
    settings = get_settings()
    if not db.scalar(select(User).where(User.email == settings.initial_admin_email.lower())):
        db.add(User(email=settings.initial_admin_email.lower(), password_hash=password_hash.hash(settings.initial_admin_password)))
        db.commit()


def create_token(user: User) -> str:
    settings = get_settings()
    expires = datetime.now(timezone.utc) + timedelta(hours=8)
    return jwt.encode({"sub": str(user.id), "email": user.email, "exp": expires}, settings.secret_key, algorithm="HS256")


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials: raise HTTPException(401, "Authentication required")
    try:
        subject = jwt.decode(credentials.credentials, get_settings().secret_key, algorithms=["HS256"])["sub"]
    except (jwt.InvalidTokenError, KeyError): raise HTTPException(401, "Invalid or expired session")
    user = db.get(User, int(subject))
    if not user: raise HTTPException(401, "Unknown user")
    return user
