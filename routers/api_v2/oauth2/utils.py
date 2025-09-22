from datetime import datetime, timedelta, timezone

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
