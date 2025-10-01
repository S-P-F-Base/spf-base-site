import json
import logging
import re
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

import utils.admin
import utils.error
from templates import templates

router = APIRouter()
logger = logging.getLogger(__name__)

LORE_CHAR_DATA = Path("data/lore_char.json")
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
_ALLOWED_STATUS = {"free", "taken", "blocked"}


def load_chars() -> dict:
    if LORE_CHAR_DATA.exists():
        try:
            return json.loads(LORE_CHAR_DATA.read_text(encoding="utf-8"))

        except Exception as e:
            logger.exception("Failed to read lore_char.json: %s", e)
            return {}

    return {}


def save_chars(data: dict) -> None:
    try:
        LORE_CHAR_DATA.parent.mkdir(parents=True, exist_ok=True)
        LORE_CHAR_DATA.write_text(
            json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8"
        )

    except Exception as e:
        logger.exception("Failed to write lore_char.json: %s", e)
        utils.error.server_error("lore_chars_write_failed", "Failed to persist data")


def next_id(chars: dict) -> str:
    numeric = [int(k) for k in chars.keys() if str(k).isdigit()]
    return str((max(numeric) if numeric else 0) + 1)


@router.get("/profile/admin/lore_chars")
async def admin_lore_chars(request: Request):
    utils.admin.require_access(request, "edit_lore_chars")
    chars = load_chars()

    items = [
        {
            "id": cid,
            "name": (c or {}).get("name", ""),
            "wiki": (c or {}).get("wiki", ""),
            "status": (c or {}).get("status", "free"),
        }
        for cid, c in chars.items()
    ]
    items.sort(key=lambda x: x["name"].lower())

    return templates.TemplateResponse(
        "profile/admin/lore_chars.html",
        {"request": request, "authenticated": True, "chars": items},
    )


@router.post("/profile/admin/lore_char/create")
async def lore_char_create(
    request: Request,
    name: str = Form(...),
    wiki: str = Form(""),
    status: str = Form("free"),
):
    utils.admin.require_access(request, "edit_lore_chars")

    clean_name = (name or "").strip()
    if not clean_name:
        utils.error.bad_request("char_name_empty", "Character name cannot be empty")

    clean_status = (status or "free").strip().lower()
    if clean_status not in _ALLOWED_STATUS:
        utils.error.bad_request("status_invalid", "Invalid status", status=clean_status)

    clean_wiki = (wiki or "").strip()
    if clean_wiki and not _URL_RE.match(clean_wiki):
        utils.error.bad_request("wiki_invalid", "Wiki URL must start with http(s)")

    chars = load_chars()
    cid = next_id(chars)
    chars[cid] = {"name": clean_name, "wiki": clean_wiki, "status": clean_status}
    save_chars(chars)

    return RedirectResponse("/profile/admin/lore_chars", status_code=303)


@router.post("/profile/admin/lore_char/update")
async def lore_char_update(
    request: Request,
    char_id: str = Form(...),
    name: str = Form(...),
    wiki: str = Form(""),
    status: str = Form("free"),
):
    utils.admin.require_access(request, "edit_lore_chars")

    chars = load_chars()
    if char_id not in chars:
        utils.error.not_found("char_not_found", "Character not found", char_id=char_id)

    clean_name = (name or "").strip()
    if not clean_name:
        utils.error.bad_request("char_name_empty", "Character name cannot be empty")

    clean_status = (status or "free").strip().lower()
    if clean_status not in _ALLOWED_STATUS:
        utils.error.bad_request("status_invalid", "Invalid status", status=clean_status)

    clean_wiki = (wiki or "").strip()
    if clean_wiki and not _URL_RE.match(clean_wiki):
        utils.error.bad_request("wiki_invalid", "Wiki URL must start with http(s)")

    chars[char_id].update(
        {"name": clean_name, "wiki": clean_wiki, "status": clean_status}
    )
    save_chars(chars)

    return RedirectResponse("/profile/admin/lore_chars", status_code=303)


@router.post("/profile/admin/lore_char/delete")
async def lore_char_delete(request: Request, char_id: str = Form(...)):
    utils.admin.require_access(request, "edit_lore_chars")

    chars = load_chars()
    if char_id in chars:
        chars.pop(char_id)
        save_chars(chars)

    return RedirectResponse("/profile/admin/lore_chars", status_code=303)
