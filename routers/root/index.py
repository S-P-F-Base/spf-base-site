from datetime import datetime

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from markdown import Markdown

from data_control import ServerControl
from templates import templates

from .wiki.wiki_render import WIKI_DIR

router = APIRouter()
NEWS_DIR = WIKI_DIR / "docs" / "news"
RU_MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}


def get_latest_news(limit: int = 3):
    items = []
    for md_file in NEWS_DIR.glob("*.md"):
        if md_file.name.lower() == "index.md":
            continue

        text = md_file.read_text(encoding="utf-8")
        head = []
        for line in text.splitlines():
            if not line.strip():
                break
            head.append(line)

        head_text = "\n".join(head)

        md = Markdown(extensions=["meta"])
        md.convert(head_text)
        meta = getattr(md, "Meta", {})

        title = meta.get("title", [md_file.stem])[0]
        date_raw = meta.get("date", [None])[0]
        dt = parse_date_any(date_raw, md_file.stat().st_mtime)

        href = "/wiki/docs/news/" + md_file.stem

        items.append({"title": title, "date": dt, "href": href})

    items.sort(key=lambda x: x["date"], reverse=True)
    return items[:limit]


def parse_date_any(raw: str | str, fallback_ts: float) -> datetime:
    if not raw:
        return datetime.fromtimestamp(fallback_ts)

    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw, fmt)

        except ValueError:
            pass

    parts = raw.split()
    if len(parts) >= 3:
        try:
            day = int(parts[0])
            month = RU_MONTHS[parts[1].lower()]
            year = int(parts[2])
            return datetime(year, month, day)

        except Exception:
            pass

    return datetime.fromtimestamp(fallback_ts)


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    status = ServerControl.get_status()
    latest_news = get_latest_news(3)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "server_status": status,
            "news": latest_news,
        },
    )
