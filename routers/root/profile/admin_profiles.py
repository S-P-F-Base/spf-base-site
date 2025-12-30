import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, StreamingResponse

import utils.admin
import utils.error
import utils.steam
from data_class import ProfileData, ProfileDataBase
from discord_bot import bot
from templates import templates

logger = logging.getLogger(__name__)
router = APIRouter()
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)

# Admin: labels
ACCESS_FIELDS = {
    "full_access": "Полный доступ",
    "panel_access": "Доступ в админ-панель",
    "edit_profiles": "Редактировать профили",
    "edit_chars": "Редактировать персонажей",
    "edit_notes": "Редактировать заметки",
    "edit_lore_chars": "Редактировать лорных персонажей",
    "edit_services": "Управлять услугами",
    "edit_payments": "Управлять оплатой",
    "server_control": "Управление игровым сервером",
}

BLACKLIST_FIELDS = {
    "chars": "ЧС: новые персонажи",
    "lore_chars": "ЧС: лорные персонажи",
    "admin": "ЧС: администрация",
}


def _as_float(x, d=0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(d)


def _as_int(x, d=0) -> int:
    try:
        return int(x)
    except Exception:
        try:
            return int(float(x))
        except Exception:
            return int(d)


def _build_view_for_profile(p: dict, extra: Optional[dict]) -> dict:
    data: ProfileData = p.get("data", ProfileData())
    if not isinstance(data, ProfileData):
        data = ProfileData()  # fail-safe

    username = (extra or {}).get("username") or p.get("username") or "Без имени"
    avatar_url = (
        (extra or {}).get("avatar_url")
        or p.get("avatar_url")
        or "/static/images/logo/discord.png"
    )

    return {
        "uuid": p.get("uuid"),
        "discord_id": p.get("discord_id"),
        "steam_id": p.get("steam_id"),
        "username": username,
        "avatar_url": avatar_url,
        "access": dict(getattr(data, "access", {}) or {}),
        "has_blacklist": bool(getattr(data, "has_blacklist", False)),
        "blacklist": {
            "chars": bool(data.blacklist.get("chars", False)),
            "lore_chars": bool(data.blacklist.get("lore_chars", False)),
            "admin": bool(data.blacklist.get("admin", False)),
        },
        "limits": {
            "base_limit": _as_float(data.limits.get("base_limit", 0)),
            "donate_limit": _as_float(data.limits.get("donate_limit", 0)),
            "used": _as_float(data.limits.get("used", 0)),
            "base_char": _as_int(data.limits.get("base_char", 0)),
            "donate_char": _as_int(data.limits.get("donate_char", 0)),
        },
        "notes": list(data.notes or []),
        "chars": list(data.chars or []),
    }


def _matches_rough(p: dict, q: str) -> bool:
    if not q:
        return True

    ql = q.lower()
    for key in ("uuid", "discord_id", "steam_id"):
        val = p.get(key) or ""
        if isinstance(val, str) and ql in val.lower():
            return True

    uname = (p.get("username") or "").lower()
    if uname and ql in uname:
        return True

    return False


@router.get("/profile/admin/profiles")
async def profile_admin_profiles(request: Request):
    utils.admin.require_admin(request)
    q = (request.query_params.get("q") or "").strip()

    profiles = ProfileDataBase.get_all_profiles()
    prefiltered = [p for p in profiles if _matches_rough(p, q)]

    light = [
        _build_view_for_profile(
            p,
            extra={
                "username": p.get("username") or "Загрузка...",
                "avatar_url": p.get("avatar_url") or "/static/images/logo/discord.png",
            },
        )
        for p in (prefiltered if q else profiles)
    ]

    return templates.TemplateResponse(
        "profile/admin/profiles.html",
        {
            "request": request,
            "authenticated": True,
            "users": light,
            "q": q,
            "ACCESS_FIELDS": ACCESS_FIELDS,
            "BLACKLIST_FIELDS": BLACKLIST_FIELDS,
        },
    )


@router.get("/profile/admin/profiles/stream")
async def profile_admin_profiles_stream(request: Request):
    utils.admin.require_admin(request)
    q = (request.query_params.get("q") or "").strip()

    profiles = ProfileDataBase.get_all_profiles()
    use_for_names = [p for p in profiles if _matches_rough(p, q)]
    if q and not use_for_names:
        use_for_names = profiles

    use_for_names = sorted(
        use_for_names,
        key=lambda p: (
            (p.get("username") or "").lower(),
            p.get("discord_id") or "",
            p.get("uuid") or "",
        ),
    )

    cog = bot.get_cog("UserControlCog")
    sem = asyncio.Semaphore(8)

    async def fetch_one(p: dict):
        extra = {}
        did = p.get("discord_id")
        if did and cog:
            try:
                async with sem:
                    info = await cog.get_user_info(int(did))  # type: ignore
                    extra = info or {}
            except Exception:
                extra = {}
        return _build_view_for_profile(p, extra)

    tasks = [asyncio.create_task(fetch_one(p)) for p in use_for_names]

    async def gen():
        try:
            for coro in asyncio.as_completed(tasks):
                if await request.is_disconnected():
                    break
                try:
                    view = await coro
                except Exception:
                    view = {
                        "uuid": None,
                        "username": "???",
                        "avatar_url": "/static/images/logo/discord.png",
                        "discord_id": None,
                    }

                if q:
                    uname = (view.get("username") or "").lower()
                    ids = (
                        (view.get("uuid") or ""),
                        (view.get("discord_id") or ""),
                        (view.get("steam_id") or ""),
                    )
                    ql = q.lower()
                    if not (
                        ql in uname
                        or any(isinstance(x, str) and ql in x.lower() for x in ids)
                    ):
                        continue

                line = json.dumps(view, ensure_ascii=False)
                yield (line + "\n").encode("utf-8")

        finally:
            for t in tasks:
                if not t.done():
                    t.cancel()

    return StreamingResponse(
        gen(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store"},
    )


@router.post("/profile/admin/profile/update")
async def profile_admin_update(request: Request):
    admin = utils.admin.require_access(request, "edit_profiles")

    form = await request.form()
    uuid = (form.get("uuid") or "").strip()  # type: ignore
    if not uuid:
        utils.error.bad_request("uuid_required", "Missing profile uuid")

    target = ProfileDataBase.get_profile_by_uuid(uuid)
    if not target:
        utils.error.not_found(
            "profile_utils.error.not_found", "Profile not found", uuid=uuid
        )

    data: ProfileData = target.get("data", ProfileData())  # type: ignore
    if not isinstance(data, ProfileData):
        utils.error.server_error(
            "profile_data_invalid", "Profile data has invalid type", uuid=uuid
        )

    access_checked = {
        k[len("access_") :] for k in form.keys() if k.startswith("access_")
    }
    admin_data: ProfileData = admin.get("data", ProfileData())  # type: ignore

    for key in ACCESS_FIELDS.keys():
        if admin_data.has_access(key):
            data.access[key] = key in access_checked

    bl_checked = {
        k[len("blacklist_") :] for k in form.keys() if k.startswith("blacklist_")
    }
    for key in BLACKLIST_FIELDS.keys():
        data.blacklist[key] = key in bl_checked

    def f(name: str, default: float = 0.0) -> float:
        try:
            return float(form.get(name, default))  # type: ignore

        except Exception:
            return float(default)

    def i(name: str, default: int = 0) -> int:
        try:
            return int(float(form.get(name, default)))  # type: ignore

        except Exception:
            return int(default)

    data.limits["base_limit"] = f("base_limit", 0.0)
    data.limits["donate_limit"] = f("donate_limit", 0.0)
    data.limits["used"] = f("used", 0.0)
    data.limits["base_char"] = i("base_char", 0)
    data.limits["donate_char"] = i("donate_char", 0)

    try:
        ProfileDataBase.update_profile(uuid, data=data)

    except Exception as e:
        logger.exception("update_profile failed: %s", e)
        utils.error.server_error(
            "profile_update_failed", "Failed to update profile", uuid=uuid
        )

    return RedirectResponse(url="/profile/admin/profiles", status_code=303)


@router.post("/profile/admin/profile/delete")
async def profile_admin_delete(request: Request, uuid: str = Form(...)):
    admin = utils.admin.require_access(request, "edit_profiles")
    if admin.get("uuid") == uuid:  # type: ignore
        utils.error.bad_request(
            "cannot_delete_self", "Admin cannot delete their own profile", uuid=uuid
        )

    try:
        ProfileDataBase.delete_profile(uuid)

    except Exception as e:
        logger.exception("delete_profile failed: %s", e)
        utils.error.server_error(
            "profile_delete_failed", "Failed to delete profile", uuid=uuid
        )

    return RedirectResponse(url="/profile/admin/profiles", status_code=303)


@router.post("/profile/admin/note/add")
async def profile_admin_note_add(
    request: Request,
    uuid: str = Form(...),
    content: str = Form(...),
    status: str = Form("info"),
):
    utils.admin.require_access(request, "edit_notes")

    target = ProfileDataBase.get_profile_by_uuid(uuid)
    if not target:
        utils.error.not_found(
            "profile_utils.error.not_found", "Profile not found", uuid=uuid
        )

    data: ProfileData = target.get("data", ProfileData())  # type: ignore
    if not isinstance(data, ProfileData):
        utils.error.server_error(
            "profile_data_invalid", "Profile data has invalid type", uuid=uuid
        )

    content_clean = (content or "").strip()
    if not content_clean:
        utils.error.bad_request("note_empty", "Note content cannot be empty", uuid=uuid)

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
        utils.error.server_error(
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
    utils.admin.require_access(request, "edit_chars")

    target = ProfileDataBase.get_profile_by_uuid(uuid)
    if not target:
        utils.error.not_found(
            "profile_utils.error.not_found", "Profile not found", uuid=uuid
        )

    data = target.get("data", ProfileData())  # type: ignore
    if not isinstance(data, ProfileData):
        utils.error.server_error(
            "profile_data_invalid", "Profile data has invalid type", uuid=uuid
        )

    clean_name = (name or "").strip()
    if not clean_name:
        utils.error.bad_request(
            "char_name_empty", "Character name cannot be empty", uuid=uuid
        )

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
        utils.error.server_error(
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
    utils.admin.require_access(request, "edit_chars")

    target = ProfileDataBase.get_profile_by_uuid(uuid)
    if not target:
        utils.error.not_found(
            "profile_utils.error.not_found", "Profile not found", uuid=uuid
        )

    data = target.get("data", ProfileData())  # type: ignore
    if not isinstance(data, ProfileData):
        utils.error.server_error(
            "profile_data_invalid", "Profile data has invalid type", uuid=uuid
        )

    if index < 0 or index >= len(data.chars):
        utils.error.bad_request(
            "char_index_invalid", "Invalid character index", uuid=uuid, index=index
        )

    data.chars.pop(index)
    total_mb = round(sum(c.get("weight_mb", 0) for c in data.chars), 2)
    data.limits["used"] = total_mb

    try:
        ProfileDataBase.update_profile(uuid, data=data)

    except Exception as e:
        logger.exception("delete_profile_char failed: %s", e)
        utils.error.server_error(
            "profile_update_failed", "Failed to delete character", uuid=uuid
        )

    return RedirectResponse(url="/profile/admin/profiles", status_code=303)


@router.post("/profile/admin/profile/create")
async def profile_admin_create(
    request: Request,
    discord_id: str = Form(...),
    steam_input: str = Form(...),
):
    utils.admin.require_access(request, "edit_profiles")

    did = (discord_id or "").strip()
    if not did.isdigit():
        utils.error.bad_request(
            "discord_id_invalid", "discord_id must be a numeric string", value=did
        )

    try:
        sid64 = utils.steam.normalize_steam_input(steam_input)

    except Exception as e:
        logger.exception("normalize_steam_input failed: %s", e)
        utils.error.server_error(
            "steam_normalize_failed",
            "Failed to normalize Steam input",
            input=steam_input,
        )
        return

    if not sid64:
        utils.error.bad_request(
            "steam_input_unsupported",
            "Unsupported Steam input format",
            input=steam_input,
        )

    all_profiles = ProfileDataBase.get_all_profiles()
    if any(p.get("discord_id") == did for p in all_profiles):
        utils.error.bad_request(
            "discord_id_conflict", "Discord ID already exists", discord_id=did
        )

    if any(p.get("steam_id") == sid64 for p in all_profiles):
        utils.error.bad_request(
            "steam_id_conflict", "Steam ID already exists", steam_id=sid64
        )

    try:
        ProfileDataBase.create_profile(discord_id=did, steam_id=sid64)

    except Exception as e:
        logger.exception("create_profile failed: %s", e)
        utils.error.server_error(
            "profile_create_failed",
            "Failed to create profile",
            discord_id=did,
            steam_id=sid64,
        )

    return RedirectResponse(url="/profile/admin/profiles", status_code=303)


@router.post("/profile/admin/recalc_roles")
async def profile_admin_recalc_roles(request: Request):
    utils.admin.require_access(request, "edit_profiles")

    cog = bot.get_cog("UserControlCog")
    if not cog or not hasattr(cog, "get_role_value"):
        utils.error.failed_dep(
            "cog_unavailable", "UserControlCog.get_role_value is not available"
        )

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
    utils.admin.require_access(request, "edit_chars")

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
