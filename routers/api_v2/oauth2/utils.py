from datetime import datetime, timedelta, timezone

from fastapi.requests import Request
from jose import JWTError, jwt

from data_control import Config


def create_jwt(data: dict) -> str:
    data = data.copy()
    data["exp"] = datetime.now(timezone.utc) + timedelta(days=30)
    return jwt.encode(data, Config.jwt_key(), algorithm="HS256")


def decode_jwt(token: str) -> dict | None:
    try:
        return jwt.decode(token, Config.jwt_key(), algorithms=["HS256"])

    except JWTError:
        return None


def merge_with_old(request: Request, new_data: dict) -> dict:
    token = request.cookies.get("session")
    merged = {}
    if token:
        old = decode_jwt(token)
        if old:
            merged.update(old)

    merged.update(new_data)
    return merged
