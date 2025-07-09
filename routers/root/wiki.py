import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from markdown import Markdown

router = APIRouter()
templates = Jinja2Templates(directory="templates")

BASE_DIR = Path(__file__).resolve().parents[2]
WIKI_DIR = BASE_DIR / "wiki"


def preprocess_wikilinks(md_text: str) -> str:
    pattern = re.compile(r"\[\[([^\|\]]+)\|([^\]]+)\]\]")
    return pattern.sub(r"[\2](/wiki/\1)", md_text)


@router.get("/wiki/{page:path}", response_class=HTMLResponse)
def wiki_page(request: Request, page: Path):
    md_path = (WIKI_DIR / page).with_suffix(".md")
    if not md_path.resolve().is_relative_to(WIKI_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Invalid path")

    try:
        content = md_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Page not found")

    md = Markdown(
        extensions=[
            "fenced_code",  # Блоки кода через тройные кавычки (```), как на GitHub
            "nl2br",  # Превращает одиночные \n в <br />
            "tables",  # Markdown-таблицы
            "meta",  # Заголовки-мета в начале файла (например, автор, дата)
            "wikilinks",  # Поддержка [[WikiLinks]] для вики-стилей
            "toc",  # 	Автоматическое оглавление по заголовкам
        ],
        extension_configs={
            "wikilinks": {
                "base_url": "/wiki/",
                "end_url": "",
                "html_class": "wikilink",
            }
        },
    )
    content = preprocess_wikilinks(content)
    rendered_html = md.convert(content)
    meta = getattr(md, "Meta", {})

    title = meta.get("title", [str(page)])[0] if meta else str(page)

    return templates.TemplateResponse(
        "wiki_template.html",
        {
            "request": request,
            "content": rendered_html,
            "title": title,
            "meta": meta,
        },
    )
