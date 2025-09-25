from datetime import UTC, datetime, timedelta
from typing import Final, Literal

from fastapi import HTTPException, Request, status
from jose import ExpiredSignatureError, JWTError, jwt

from data_bases.user_db import UserDB

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
        return cls.create({"usr": login, "typ": "acc"}, expires_delta)

    @classmethod
    def create_refresh(cls, login: str, expires_delta: timedelta | None = None) -> str:
        return cls.create(
            {"usr": login, "typ": "ref"},
            expires_delta or timedelta(days=cls._REFRESH_EXPIRE_DAYS),
        )

    @classmethod
    def decode(cls, token: str) -> dict:
        payload = jwt.decode(token, Config.jwt_key(), algorithms=[cls._ALGORITHM])
        return payload


def _get_authorization_header_payload(request: Request, header_name: str) -> str:
    auth = request.headers.get(header_name)
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing or invalid {header_name} header",
        )

    token = auth.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing or invalid {header_name} header",
        )

    return token


def _jwt_sanity_check(token: str, type: Literal["ref", "acc"]) -> str:
    try:
        payload = JWTControl.decode(token)

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    if payload.get("typ") != type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user = payload.get("usr")
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token struct",
        )

    if not UserDB.user_exists(user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token user",
        )

    return user


def req_authorization(request: Request) -> str:
    token = _get_authorization_header_payload(request, "Authorization")
    return _jwt_sanity_check(token, "acc")


def req_refresh(request: Request) -> str:
    token = _get_authorization_header_payload(request, "X-Authorization-Refresh")
    return _jwt_sanity_check(token, "ref")
