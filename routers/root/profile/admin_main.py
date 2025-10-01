import logging

from fastapi import APIRouter, Request

import utils.admin
from templates import templates

router = APIRouter()

logging.basicConfig(level=logging.INFO)


@router.get("/profile/admin")
async def profile_admin_home(request: Request):
    admin = utils.admin.require_admin(request)
    return templates.TemplateResponse(
        "profile/admin/index.html",
        {"request": request, "authenticated": True, "profile": admin},
    )
