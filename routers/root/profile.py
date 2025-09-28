import asyncio
import logging
import re
from datetime import UTC, datetime
from typing import Any, Optional

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse

import utils.jwt
import utils.steam
from data_class import ProfileData, ProfileDataBase
from discord_bot import bot
from templates import templates

logger = logging.getLogger(__name__)
router = APIRouter()
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


# Error helpers (uniform)
def _bad_request(code: str, message: str, **extra) -> None:
    payload: dict[str, Any] = {"code": code, "message": message}
    if extra:
        payload["context"] = extra

    raise HTTPException(status_code=400, detail=payload)


def _forbidden(code: str, message: str, **extra) -> None:
    payload: dict[str, Any] = {"code": code, "message": message}
    if extra:
        payload["context"] = extra

    raise HTTPException(status_code=403, detail=payload)


def _not_found(code: str, message: str, **extra) -> None:
    payload: dict[str, Any] = {"code": code, "message": message}
    if extra:
        payload["context"] = extra

    raise HTTPException(status_code=404, detail=payload)


def _failed_dep(code: str, message: str, **extra) -> None:
    payload: dict[str, Any] = {"code": code, "message": message}
    if extra:
        payload["context"] = extra

    raise HTTPException(status_code=424, detail=payload)


def _server_error(code: str, message: str, **extra) -> None:
    payload: dict[str, Any] = {"code": code, "message": message}
    if extra:
        payload["context"] = extra

    raise HTTPException(status_code=500, detail=payload)


# Auth helpers
def _get_admin_profile(request: Request):
    token = request.cookies.get("session")
    decoded = utils.jwt.decode(token) if token else None
    if not decoded:
        return None

    uuid = decoded.get("uuid")
    if not uuid:
        return None

    profile = ProfileDataBase.get_profile_by_uuid(uuid)
    if not profile:
        return None

    raw = profile.get("data", ProfileData())
    if not isinstance(raw, ProfileData):
        return None

    return profile if raw.has_access("panel_access") else None


def _require_admin(request: Request) -> dict:
    admin = _get_admin_profile(request)
    if admin is None:
        _forbidden(
            "admin_required", "Admin privileges required to access this endpoint"
        )

    return admin  # type: ignore


def _require_access(request: Request, perm: str) -> dict:
    admin = _require_admin(request)
    raw = admin.get("data", ProfileData())
    if not isinstance(raw, ProfileData):
        _forbidden("admin_data_invalid", "Admin profile data is invalid")

    if not raw.has_access(perm):
        _forbidden(f"{perm}_required", f"Permission '{perm}' is required")

    return admin


# Public pages
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


# Admin: main dashboard
@router.get("/profile/admin")
async def profile_admin_home(request: Request):
    admin = _require_admin(request)
    return templates.TemplateResponse(
        "profile/admin/index.html",
        {"request": request, "authenticated": True, "profile": admin},
    )


# Admin: list & view (moved to /profiles)
ACCESS_FIELDS = {
    "full_access": "Полный доступ",
    #
    "panel_access": "Доступ в админ-панель",
    #
    "edit_profiles": "Редактировать профили",
    "edit_chars": "Редактировать персонажей",
    "edit_notes": "Редактировать заметки",
    #
    "server_control": "Управление игровым сервером",
}

BLACKLIST_FIELDS = {
    "chars": "ЧС: новые персонажи",
    "lore_chars": "ЧС: лорные персонажи",
    "admin": "ЧС: администрация",
}


@router.get("/profile/admin/profiles")
async def profile_admin_profiles(request: Request):
    _require_admin(request)

    q = (request.query_params.get("q") or "").strip().lower()
    profiles = ProfileDataBase.get_all_profiles()

    def matches_rough(p: dict) -> bool:
        if not q:
            return True
        for key in ("uuid", "discord_id", "steam_id"):
            val = p.get(key) or ""
            if isinstance(val, str) and q in val.lower():
                return True
        return False

    rough = [p for p in profiles if matches_rough(p)]
    use_for_names = rough if rough else profiles

    cog = bot.get_cog("UserControlCog")
    extra_map: dict[int, dict] = {}
    if cog:
        tasks, index_map = [], []
        for i, p in enumerate(use_for_names):
            did = p.get("discord_id")
            if did:
                tasks.append(cog.get_user_info(did))  # type: ignore
                index_map.append(i)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for idx, res in zip(index_map, results):
                extra_map[idx] = {} if isinstance(res, Exception) else (res or {})  # type: ignore

    def as_float(x, d=0.0):
        try:
            return float(x)

        except Exception:
            return d

    def as_int(x, d=0):
        try:
            return int(x)

        except Exception:
            try:
                return int(float(x))

            except Exception:
                return d

    def build_view(p: dict, extra: Optional[dict]) -> dict:
        data: ProfileData = p.get("data", ProfileData())
        username = (extra or {}).get("username") or "Без имени"
        avatar_url = (extra or {}).get("avatar_url") or p.get("avatar_url") or ""
        return {
            "uuid": p.get("uuid"),
            "discord_id": p.get("discord_id"),
            "steam_id": p.get("steam_id"),
            "username": username,
            "avatar_url": avatar_url,
            "access": data.access,
            "has_blacklist": data.has_blacklist,
            "blacklist": {
                "chars": data.blacklist.get("chars", False),
                "lore_chars": data.blacklist.get("lore_chars", False),
                "admin": data.blacklist.get("admin", False),
            },
            "limits": {
                "base_limit": as_float(data.limits.get("base_limit", 0)),
                "donate_limit": as_float(data.limits.get("donate_limit", 0)),
                "used": as_float(data.limits.get("used", 0)),
                "base_char": as_int(data.limits.get("base_char", 0)),
                "donate_char": as_int(data.limits.get("donate_char", 0)),
            },
            "notes": data.notes,
            "chars": data.chars,
        }

    view_pool = [build_view(p, extra_map.get(i)) for i, p in enumerate(use_for_names)]
    if q and not rough:
        view_pool = [u for u in view_pool if q in (u["username"] or "").lower()]

    return templates.TemplateResponse(
        "profile/admin/profiles.html",
        {
            "request": request,
            "authenticated": True,
            "users": view_pool,
            "q": q,
            "ACCESS_FIELDS": ACCESS_FIELDS,
            "BLACKLIST_FIELDS": BLACKLIST_FIELDS,
        },
    )


# Admin: update/delete (permissions)
@router.post("/profile/admin/profile/update")
async def profile_admin_update(
    request: Request,
    uuid: str = Form(...),
    access_panel: bool = Form(False),
    access_edit_profiles: bool = Form(False),
    access_edit_chars: bool = Form(False),
    access_edit_notes: bool = Form(False),
    access_full: bool = Form(False),
    blacklist_chars: bool = Form(False),
    blacklist_lore: bool = Form(False),
    blacklist_admin: bool = Form(False),
    base_limit: float = Form(0.0),
    donate_limit: float = Form(0.0),
    used: float = Form(0.0),
    base_char: int = Form(0),
    donate_char: int = Form(0),
):
    _require_access(request, "edit_profiles")

    target = ProfileDataBase.get_profile_by_uuid(uuid)
    if not target:
        _not_found("profile_not_found", "Profile not found", uuid=uuid)

    data: ProfileData = target.get("data", ProfileData())  # type: ignore
    if not isinstance(data, ProfileData):
        _server_error(
            "profile_data_invalid", "Profile data has invalid type", uuid=uuid
        )

    # Access
    data.access["full_access"] = bool(access_full)
    data.access["panel_access"] = bool(access_panel)
    data.access["edit_profiles"] = bool(access_edit_profiles)
    data.access["edit_chars"] = bool(access_edit_chars)
    data.access["edit_notes"] = bool(access_edit_notes)

    # Blacklist
    data.blacklist["chars"] = bool(blacklist_chars)
    data.blacklist["lore_chars"] = bool(blacklist_lore)
    data.blacklist["admin"] = bool(blacklist_admin)

    # Limits
    data.limits["base_limit"] = float(base_limit)
    data.limits["donate_limit"] = float(donate_limit)
    data.limits["used"] = float(used)
    data.limits["base_char"] = int(base_char)
    data.limits["donate_char"] = int(donate_char)

    try:
        ProfileDataBase.update_profile(uuid, data=data)
    except Exception as e:
        logger.exception("update_profile failed: %s", e)
        _server_error("profile_update_failed", "Failed to update profile", uuid=uuid)

    return RedirectResponse(url="/profile/admin/profiles", status_code=303)


@router.post("/profile/admin/profile/delete")
async def profile_admin_delete(request: Request, uuid: str = Form(...)):
    admin = _require_access(request, "edit_profiles")

    if admin.get("uuid") == uuid:
        _bad_request(
            "cannot_delete_self", "Admin cannot delete their own profile", uuid=uuid
        )

    try:
        ProfileDataBase.delete_profile(uuid)
    except Exception as e:
        logger.exception("delete_profile failed: %s", e)
        _server_error("profile_delete_failed", "Failed to delete profile", uuid=uuid)

    return RedirectResponse(url="/profile/admin/profiles", status_code=303)


# Admin: notes & chars (permissions)
@router.post("/profile/admin/note/add")
async def profile_admin_note_add(
    request: Request,
    uuid: str = Form(...),
    content: str = Form(...),
    status: str = Form("info"),
):
    _require_access(request, "edit_notes")

    target = ProfileDataBase.get_profile_by_uuid(uuid)
    if not target:
        _not_found("profile_not_found", "Profile not found", uuid=uuid)

    data: ProfileData = target.get("data", ProfileData())  # type: ignore
    if not isinstance(data, ProfileData):
        _server_error(
            "profile_data_invalid", "Profile data has invalid type", uuid=uuid
        )

    content_clean = (content or "").strip()
    if not content_clean:
        _bad_request("note_empty", "Note content cannot be empty", uuid=uuid)

    notes = data.notes
    notes.insert(
        0,
        {
            "date": datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M"),
            "status": (status or "info").strip().lower(),
            "content": content_clean,
        },
    )
    data.notes = notes

    try:
        ProfileDataBase.update_profile(uuid, data=data)

    except Exception as e:
        logger.exception("update_profile (note) failed: %s", e)
        _server_error(
            "profile_update_failed", "Failed to update profile with note", uuid=uuid
        )

    return RedirectResponse(url="/profile/admin/profiles", status_code=303)


@router.post("/profile/admin/char/add")
async def profile_admin_char_add(
    request: Request,
    uuid: str = Form(...),
    name: str = Form(...),
    discord_url: str = Form(""),
    steam_urls: str = Form(""),
):
    _require_access(request, "edit_chars")

    target = ProfileDataBase.get_profile_by_uuid(uuid)
    if not target:
        _not_found("profile_not_found", "Profile not found", uuid=uuid)

    data = target.get("data", ProfileData())  # type: ignore
    if not isinstance(data, ProfileData):
        _server_error(
            "profile_data_invalid", "Profile data has invalid type", uuid=uuid
        )

    clean_name = (name or "").strip()
    if not clean_name:
        _bad_request("char_name_empty", "Character name cannot be empty", uuid=uuid)

    ids: list[str] = []
    for part in re.split(r"[\s,]+", (steam_urls or "").strip()):
        m = re.search(r"[?&]id=(\d+)", part)
        if m:
            ids.append(m.group(1))

    sizes = utils.steam.fetch_workshop_sizes(ids)
    total_size = sum(sizes.values())
    total_mb = round(total_size / 1024 / 1024, 2)

    entry = {
        "name": clean_name,
        "discord_url": (discord_url or "").strip()
        if _URL_RE.match(discord_url or "")
        else "",
        "steam_urls": [
            f"https://steamcommunity.com/sharedfiles/filedetails/?id={i}" for i in ids
        ],
        "weight_mb": total_mb,
    }

    chars = data.chars
    chars.append(entry)
    data.chars = chars
    data.limits["used"] = round(sum(ch.get("weight_mb", 0) for ch in chars), 2)

    try:
        ProfileDataBase.update_profile(uuid, data=data)

    except Exception as e:
        logger.exception("update_profile (char) failed: %s", e)
        _server_error(
            "profile_update_failed",
            "Failed to update profile with character",
            uuid=uuid,
        )

    return RedirectResponse(url="/profile/admin/profiles", status_code=303)


@router.post("/profile/admin/char/delete")
async def profile_admin_char_delete(
    request: Request,
    uuid: str = Form(...),
    index: int = Form(...),
):
    _require_access(request, "edit_chars")

    target = ProfileDataBase.get_profile_by_uuid(uuid)
    if not target:
        _not_found("profile_not_found", "Profile not found", uuid=uuid)

    data = target.get("data", ProfileData())  # type: ignore
    if not isinstance(data, ProfileData):
        _server_error(
            "profile_data_invalid", "Profile data has invalid type", uuid=uuid
        )

    if index < 0 or index >= len(data.chars):
        _bad_request(
            "char_index_invalid", "Invalid character index", uuid=uuid, index=index
        )

    data.chars.pop(index)
    total_mb = round(sum(c.get("weight_mb", 0) for c in data.chars), 2)
    data.limits["used"] = total_mb

    try:
        ProfileDataBase.update_profile(uuid, data=data)

    except Exception as e:
        logger.exception("delete_profile_char failed: %s", e)
        _server_error("profile_update_failed", "Failed to delete character", uuid=uuid)

    return RedirectResponse(url="/profile/admin/profiles", status_code=303)


# Admin: create & role check
@router.post("/profile/admin/profile/create")
async def profile_admin_create(
    request: Request,
    discord_id: str = Form(...),
    steam_input: str = Form(...),
):
    _require_access(request, "edit_profiles")

    did = (discord_id or "").strip()
    if not did.isdigit():
        _bad_request(
            "discord_id_invalid", "discord_id must be a numeric string", value=did
        )

    try:
        sid64 = utils.steam.normalize_steam_input(steam_input)

    except Exception as e:
        logger.exception("normalize_steam_input failed: %s", e)
        _server_error(
            "steam_normalize_failed",
            "Failed to normalize Steam input",
            input=steam_input,
        )
        return

    if not sid64:
        _bad_request(
            "steam_input_unsupported",
            "Unsupported Steam input format",
            input=steam_input,
        )

    all_profiles = ProfileDataBase.get_all_profiles()
    if any(p.get("discord_id") == did for p in all_profiles):
        _bad_request("discord_id_conflict", "Discord ID already exists", discord_id=did)

    if any(p.get("steam_id") == sid64 for p in all_profiles):
        _bad_request("steam_id_conflict", "Steam ID already exists", steam_id=sid64)

    try:
        ProfileDataBase.create_profile(discord_id=did, steam_id=sid64)

    except Exception as e:
        logger.exception("create_profile failed: %s", e)
        _server_error(
            "profile_create_failed",
            "Failed to create profile",
            discord_id=did,
            steam_id=sid64,
        )

    return RedirectResponse(url="/profile/admin/profiles", status_code=303)


@router.post("/profile/admin/recalc_roles")
async def profile_admin_recalc_roles(request: Request):
    _require_access(request, "edit_profiles")

    cog = bot.get_cog("UserControlCog")
    if not cog or not hasattr(cog, "get_role_value"):
        _failed_dep("cog_unavailable", "UserControlCog.get_role_value is not available")

    profiles = ProfileDataBase.get_all_profiles()
    sem = asyncio.Semaphore(8)

    async def update_one(p: dict):
        data = p.get("data", ProfileData())
        if not isinstance(data, ProfileData):
            logger.warning("Skip profile with invalid data type: %s", p.get("uuid"))
            return

        did_raw = (p.get("discord_id") or "").strip()
        if not did_raw.isdigit():
            logger.warning("Skip profile with non-numeric discord_id: %s", did_raw)
            return

        did = int(did_raw)
        try:
            async with sem:
                base_limit, base_char = await cog.get_role_value(did)  # type: ignore

        except Exception as e:
            logger.warning("get_role_value failed for %s: %r", did, e)
            return

        data.limits["base_limit"] = float(base_limit)
        data.limits["base_char"] = int(base_char)
        ProfileDataBase.update_profile(p["uuid"], data=data)

    await asyncio.gather(*(update_one(p) for p in profiles))
    return RedirectResponse(url="/profile/admin/profiles", status_code=303)


@router.post("/profile/admin/recalc_weights")
async def profile_admin_recalc_weights(request: Request):
    _require_access(request, "edit_chars")

    profiles = ProfileDataBase.get_all_profiles()

    async def process_profile(p: dict):
        data = p.get("data", ProfileData())
        if not isinstance(data, ProfileData):
            logger.warning("Skip profile with invalid data type: %s", p.get("uuid"))
            return

        chars = data.chars
        total_bytes = 0
        for ch in chars:
            ids: list[str] = []
            for url in ch.get("steam_urls", []):
                m = re.search(r"[?&]id=(\d+)", url)
                if m:
                    ids.append(m.group(1))

            if not ids:
                ch["weight_mb"] = 0
                continue

            sizes = utils.steam.fetch_workshop_sizes(ids)
            ch_weight = sum(sizes.values())
            ch["weight_mb"] = round(ch_weight / 1024 / 1024, 2)
            total_bytes += ch_weight

        data.chars = chars
        data.limits["used"] = round(total_bytes / 1024 / 1024, 2)
        ProfileDataBase.update_profile(p["uuid"], data=data)

    await asyncio.gather(*(process_profile(p) for p in profiles))
    return RedirectResponse(url="/profile/admin/profiles", status_code=303)
