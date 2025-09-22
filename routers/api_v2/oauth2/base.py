from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

import utils.jwt

router = APIRouter()


@router.get("/me")
def me(request: Request):
    token = request.cookies.get("session")
    if not token:
        return JSONResponse({"authenticated": False})

    data = utils.jwt.decode(token)
    if not data:
        return JSONResponse({"authenticated": False})

    return {"authenticated": True, "user": data}
