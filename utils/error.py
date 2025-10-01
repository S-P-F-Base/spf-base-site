from typing import Any

from fastapi import HTTPException


def bad_request(code: str, message: str, **extra) -> None:
    payload: dict[str, Any] = {"code": code, "message": message}
    if extra:
        payload["context"] = extra

    raise HTTPException(status_code=400, detail=payload)


def forbidden(code: str, message: str, **extra) -> None:
    payload: dict[str, Any] = {"code": code, "message": message}
    if extra:
        payload["context"] = extra

    raise HTTPException(status_code=403, detail=payload)


def not_found(code: str, message: str, **extra) -> None:
    payload: dict[str, Any] = {"code": code, "message": message}
    if extra:
        payload["context"] = extra

    raise HTTPException(status_code=404, detail=payload)


def failed_dep(code: str, message: str, **extra) -> None:
    payload: dict[str, Any] = {"code": code, "message": message}
    if extra:
        payload["context"] = extra

    raise HTTPException(status_code=424, detail=payload)


def server_error(code: str, message: str, **extra) -> None:
    payload: dict[str, Any] = {"code": code, "message": message}
    if extra:
        payload["context"] = extra

    raise HTTPException(status_code=500, detail=payload)
