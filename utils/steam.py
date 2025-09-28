import logging
import re

import requests

from data_control import Config

logger = logging.getLogger(__name__)

_STEAMID64_BASE = 76561197960265728
_VANITY_RE = re.compile(
    r"https?://steamcommunity\.com/(?:id|user)/(?P<vanity>[^/?#]+)", re.IGNORECASE
)
_PROFILES_RE = re.compile(
    r"https?://steamcommunity\.com/profiles/(?P<sid64>\d{16,20})", re.IGNORECASE
)
_STEAM2_RE = re.compile(r"^STEAM_[0-5]:(?P<y>[01]):(?P<z>\d+)$", re.IGNORECASE)
_STEAM3_RE = re.compile(r"^\[?U:1:(?P<acc>\d+)\]?$", re.IGNORECASE)


def _steam64_from_account_id(account_id: int) -> int:
    return _STEAMID64_BASE + account_id


def _parse_steam2(s: str) -> int | None:
    m = _STEAM2_RE.match(s.strip())
    if not m:
        return None

    return _steam64_from_account_id(int(m.group("z")) * 2 + int(m.group("y")))


def _parse_steam3(s: str) -> int | None:
    m = _STEAM3_RE.match(s.strip())
    return _steam64_from_account_id(int(m.group("acc"))) if m else None


def _parse_profiles_url(s: str) -> int | None:
    m = _PROFILES_RE.match(s.strip())
    return int(m.group("sid64")) if m else None


def _parse_digits_as_sid64_or_acc(s: str) -> int | None:
    s = s.strip()
    if not s.isdigit():
        return None

    val = int(s)
    return (
        val
        if val >= _STEAMID64_BASE
        else (_steam64_from_account_id(val) if val >= 1 else None)
    )


def _resolve_vanity_to_sid64(vanity: str) -> int | None:
    key = Config.steam_api()
    api_key = key() if callable(key) else None
    if not api_key:
        return None
    try:
        r = requests.get(
            "https://api.steampowered.com/ISteamUser/ResolveVanityURL/v1/",
            params={"key": api_key, "vanityurl": vanity},
            timeout=8,
        )
        r.raise_for_status()
        resp = r.json().get("response") or {}
        if int(resp.get("success", 0)) == 1:
            return int(resp.get("steamid"))  # type: ignore

    except Exception as e:
        logger.exception("Steam vanity resolve failed: %s", e)

    return None


def normalize_steam_input(raw: str) -> str | None:
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

    m = _VANITY_RE.match(s)
    if m:
        sid64 = _resolve_vanity_to_sid64(m.group("vanity"))
        return str(sid64) if sid64 else None

    if s.startswith("steam://"):
        inner = s.split("steam://", 1)[1]
        if "http" in inner:
            return normalize_steam_input(inner[inner.find("http") :])

    return None


def fetch_workshop_sizes(ids: list[str]) -> dict[str, int]:
    if not ids:
        return {}

    key = Config.steam_api()
    payload: dict[str, str] = {"key": str(key), "itemcount": str(len(ids))}
    for i, fid in enumerate(ids):
        payload[f"publishedfileids[{i}]"] = str(fid)

    try:
        r = requests.post(
            "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/",
            data=payload,
            timeout=8,
        )
        r.raise_for_status()
        details = (r.json().get("response") or {}).get("publishedfiledetails") or []

    except Exception as e:
        logger.exception("Workshop size fetch failed: %s", e)
        return {}

    out: dict[str, int] = {}
    for it in details:
        if it.get("result") == 1 and it.get("publishedfileid"):
            out[it["publishedfileid"]] = int(it.get("file_size", 0))

    return out
