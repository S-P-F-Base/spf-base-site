from fastapi import APIRouter, Request

import utils.admin
from templates import templates

router = APIRouter()


@router.get("/profile/admin")
async def profile_admin_home(request: Request):
    admin = utils.admin.require_admin(request)
    return templates.TemplateResponse(
        "profile/admin/index.html",
        {"request": request, "authenticated": True, "profile": admin},
    )
