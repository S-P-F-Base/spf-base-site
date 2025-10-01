from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

import utils.jwt
from data_class import ProfileDataBase
from discord_bot import bot
from templates import templates

router = APIRouter()


async def render_profile_page(request: Request, template_name: str):
    token = request.cookies.get("session")
    decoded = utils.jwt.decode(token) if token else None
    if not decoded:
        if template_name == "profile/index.html":
            return templates.TemplateResponse(
                template_name,
                {"request": request, "authenticated": False, "profile": {}},
            )

        return RedirectResponse("/profile")

    uuid = decoded.get("uuid")
    if not uuid:
        resp = RedirectResponse("/profile")
        resp.delete_cookie("session")
        return resp

    profile = ProfileDataBase.get_profile_by_uuid(uuid)
    if not profile:
        resp = RedirectResponse("/profile")
        resp.delete_cookie("session")
        return resp

    discord_id = profile.get("discord_id")
    if discord_id:
        cog = bot.get_cog("UserControlCog")
        if cog:
            try:
                extra = await cog.get_user_info(discord_id)  # type: ignore
                if isinstance(extra, dict):
                    profile.update(extra)

            except Exception:
                pass

    profile.pop("notes", None)
    return templates.TemplateResponse(
        template_name,
        {"request": request, "authenticated": True, "profile": profile},
    )


@router.get("/profile")
async def profile(request: Request):
    return await render_profile_page(request, "profile/index.html")


@router.get("/profile/content")
async def profile_content(request: Request):
    return await render_profile_page(request, "profile/content.html")
