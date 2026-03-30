from datetime import datetime, timedelta, timezone
from typing import Optional, Any
import bcrypt
import jwt as pyjwt
from jwt.exceptions import InvalidTokenError
from app.config import get_settings


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(
    data: dict[str, Any],
    expires_delta_seconds: Optional[int] = None,
) -> str:
    settings = get_settings()
    payload = data.copy()
    if expires_delta_seconds is not None:
        expire = datetime.now(timezone.utc) + timedelta(seconds=expires_delta_seconds)
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.jwt_expire_days)
    payload["exp"] = expire
    return pyjwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> Optional[dict[str, Any]]:
    settings = get_settings()
    try:
        return pyjwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except InvalidTokenError:
        return None
