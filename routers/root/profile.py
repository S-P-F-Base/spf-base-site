from fastapi import APIRouter, Request

import utils.jwt
from templates import templates

router = APIRouter()


@router.get("/profile")
def player(request: Request):
    token = request.cookies.get("session")
    profile = {}
    authenticated = False

    if token:
        data = utils.jwt.decode(token)
        if data:
            authenticated = True
            profile = data

    return templates.TemplateResponse(
        "profile/index.html",
        {
            "request": request,
            "authenticated": authenticated,
            "profile": profile,
        },
    )
