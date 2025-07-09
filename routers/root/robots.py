from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter()


@router.get("/robots.txt", response_class=PlainTextResponse)
def robots_txt():
    content = """
User-agent: *
Disallow: /api/
"""
    return content.strip()
