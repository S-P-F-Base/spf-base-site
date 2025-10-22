import logging
import re
from typing import Optional

import requests

from data_control import Config

logger = logging.getLogger(__name__)

_STEAMID64_BASE = 76561197960265728

_VANITY_URL_RE = re.compile(
    r"https?://steamcommunity\.com/(?:id|user)/(?P<vanity>[^/?#]+)", re.IGNORECASE
)
_PROFILES_RE = re.compile(
    r"https?://steamcommunity\.com/profiles/(?P<sid64>\d{16,20})", re.IGNORECASE
)
_STEAM2_RE = re.compile(r"^STEAM_[0-5]:(?P<y>[01]):(?P<z>\d+)$", re.IGNORECASE)
_STEAM3_RE = re.compile(r"^\[?U:1:(?P<acc>\d+)\]?$", re.IGNORECASE)

_PLAUSIBLE_VANITY_RE = re.compile(r"^[A-Za-z0-9._-]{2,64}$")


def _steam64_from_account_id(account_id: int) -> int:
    return _STEAMID64_BASE + account_id


def _parse_steam2(s: str) -> Optional[int]:
    m = _STEAM2_RE.match(s.strip())
    if not m:
        return None

    return _steam64_from_account_id(int(m.group("z")) * 2 + int(m.group("y")))


def _parse_steam3(s: str) -> Optional[int]:
    m = _STEAM3_RE.match(s.strip())
    return _steam64_from_account_id(int(m.group("acc"))) if m else None


def _parse_profiles_url(s: str) -> Optional[int]:
    m = _PROFILES_RE.match(s.strip())
    return int(m.group("sid64")) if m else None


def _parse_digits_as_sid64_or_acc(s: str) -> Optional[int]:
    s = s.strip()
    if not s.isdigit():
        return None

    val = int(s)
    if val >= _STEAMID64_BASE:
        return val

    return _steam64_from_account_id(val) if val >= 1 else None


def _resolve_vanity_via_api(vanity: str) -> Optional[int]:
    api_key = Config.steam_api()
    try:
        r = requests.get(
            "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/",
            params={"key": api_key, "vanityurl": vanity},
            timeout=8,
        )
        r.raise_for_status()
        resp = (r.json() or {}).get("response") or {}
        if int(resp.get("success", 0)) == 1 and resp.get("steamid"):
            return int(resp["steamid"])

    except Exception as e:
        logger.warning("Steam vanity resolve via API failed for %r: %s", vanity, e)

    return None


def _resolve_vanity_fallback(vanity: str) -> Optional[int]:
    for base in ("id", "user"):
        try:
            r = requests.get(
                f"https://steamcommunity.com/{base}/{vanity}?xml=1",
                timeout=8,
                headers={"Accept": "application/xml,text/xml,*/*"},
            )
            if r.status_code != 200 or "<steamID64>" not in r.text:
                continue

            m = re.search(r"<steamID64>(\d+)</steamID64>", r.text)
            if m:
                return int(m.group(1))

        except Exception as e:
            logger.warning(
                "Steam vanity fallback failed (%s) for %r: %s", base, vanity, e
            )

    return None


def _resolve_vanity_to_sid64(vanity: str) -> Optional[int]:
    return _resolve_vanity_via_api(vanity) or _resolve_vanity_fallback(vanity)


def normalize_steam_input(raw: str) -> Optional[str]:
    if not raw:
        return None

    s = raw.strip()

    sid64 = (
        _parse_profiles_url(s)
        or _parse_steam2(s)
        or _parse_steam3(s)
        or _parse_digits_as_sid64_or_acc(s)
    )
    if sid64:
        return str(sid64)

    m = _VANITY_URL_RE.match(s)
    if m:
        sid64 = _resolve_vanity_to_sid64(m.group("vanity"))
        return str(sid64) if sid64 else None

    if s.lower().startswith("steam://"):
        inner = s.split("steam://", 1)[1]
        if "http" in inner:
            http_part = inner[inner.find("http") :]
            return normalize_steam_input(http_part)

    if _PLAUSIBLE_VANITY_RE.match(s):
        sid64 = _resolve_vanity_to_sid64(s)
        return str(sid64) if sid64 else None

    return None


def fetch_workshop_sizes(ids: list[str]) -> dict[str, int]:
    if not ids:
        return {}

    api_key = Config.steam_api()
    payload: dict[str, str] = {"itemcount": str(len(ids))}
    if api_key:
        payload["key"] = api_key

    for i, fid in enumerate(ids):
        payload[f"publishedfileids[{i}]"] = str(fid)

    try:
        r = requests.post(
            "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/",
            data=payload,
            timeout=8,
        )
        r.raise_for_status()
        details = ((r.json() or {}).get("response") or {}).get(
            "publishedfiledetails"
        ) or []

    except Exception as e:
        logger.warning("Workshop size fetch failed: %s", e)
        return {}

    out: dict[str, int] = {}
    for it in details:
        if it.get("result") == 1 and it.get("publishedfileid"):
            try:
                out[str(it["publishedfileid"])] = int(it.get("file_size", 0))

            except Exception:
                continue

    return out
