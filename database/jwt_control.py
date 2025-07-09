from datetime import UTC, datetime, timedelta
from typing import Any, Final

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from .config import Config


class JWTControl:
    _ALGORITHM: Final[str] = "HS256"
    _DEFAULT_EXPIRE_MINUTES = 15
    _REFRESH_EXPIRE_DAYS = 3

    @classmethod
    def create(cls, data: dict, expires_delta: timedelta | None = None) -> str:
        to_encode = data.copy()
        expire = datetime.now(UTC) + (
            expires_delta or timedelta(minutes=cls._DEFAULT_EXPIRE_MINUTES)
        )
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, Config.jwt_key(), algorithm=cls._ALGORITHM)

    @classmethod
    def create_access(cls, login: str, expires_delta: timedelta | None = None) -> str:
        return cls.create({"usr": login}, expires_delta)

    @classmethod
    def create_refresh(cls, login: str, expires_delta: timedelta | None = None) -> str:
        return cls.create(
            {"usr": login, "typ": "ref"},
            expires_delta or timedelta(days=cls._REFRESH_EXPIRE_DAYS),
        )

    @classmethod
    def decode(cls, token: str) -> dict | None:
        try:
            payload = jwt.decode(token, Config.jwt_key(), algorithms=[cls._ALGORITHM])
            return payload

        except JWTError:
            return None


def _base_access(request: Request) -> dict[str, Any]:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = auth.removeprefix("Bearer ").strip()
    payload = JWTControl.decode(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return payload


def req_login(request: Request) -> str:
    payload = _base_access(request)

    if "usr" not in payload or payload.get("typ") == "ref":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return payload["usr"]


def req_refresh(request: Request) -> str:
    payload = _base_access(request)

    if "usr" not in payload or payload.get("typ") != "ref":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    return payload["usr"]
