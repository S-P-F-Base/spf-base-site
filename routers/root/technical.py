from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    content = """
User-agent: *
Disallow: /api/
Disallow: /download/
"""
    return content.strip()


@router.get(".well-known/discord", response_class=PlainTextResponse)
def well_known_discord():
    content = "dh=60795f3ac4184d38f6942a1963cb65ee9891885c"
    return content.strip()
