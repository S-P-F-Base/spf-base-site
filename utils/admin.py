from fastapi import Request

from data_class import ProfileData, ProfileDataBase

from .error import forbidden
from .jwt import decode


def get_admin_profile(request: Request) -> dict | None:
    token = request.cookies.get("session")
    decoded = decode(token) if token else None
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


def require_admin(request: Request) -> dict | None:
    admin = get_admin_profile(request)
    if admin is None:
        forbidden("admin_required", "Admin privileges required to access this endpoint")
        return None

    return admin


def require_access(request: Request, perm: str) -> dict | None:
    admin = require_admin(request)
    if not admin:
        forbidden("admin_required", "Admin privileges required to access this endpoint")
        return None

    raw = admin.get("data", ProfileData())
    if not isinstance(raw, ProfileData):
        forbidden("admin_data_invalid", "Admin profile data is invalid")
        return None

    if not raw.has_access(perm):
        forbidden(f"{perm}_required", f"Permission '{perm}' is required")
        return None

    return admin
